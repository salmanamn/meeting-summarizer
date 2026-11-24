"""A meeting job as the status endpoint reports it (GET /api/meetings/<id>).

uv run python scripts/meeting_status.py m01-1                 the record now, one line per stage reached
uv run python scripts/meeting_status.py m01-1 --wait 600      follow it until summarised or failed (exit 0 / 1)
uv run python scripts/meeting_status.py m01-1 --wait 120 --until received    stop once the job reached that stage
uv run python scripts/meeting_status.py m01-1 --json          the whole record
uv run python scripts/meeting_status.py m01-1 --wait 600 --evidence docs/evidence/m2-runs.md --case "..."
                                                              also append what it printed to an evidence file

--url defaults to the local host (http://127.0.0.1:7071); FUNCTION_KEY in the environment is sent as the
function key (Azure, M7). With --wait, a host that doesn't answer is asked again until the deadline. Exit 2: timed
out, or no answer from the host; --evidence is then not written.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from summarize_file import show

from meeting.summary import MeetingSummary

TERMINAL = ("summarised", "failed")
LINES: list[str] = []  # everything printed, for --evidence


def say(line: str) -> None:
    LINES.append(line)
    print(line, flush=True)


def mask(line: str) -> str:
    """Evidence carries no '@' and no home directory (the handoff's rule: mask in the command that writes it)."""
    return line.replace(str(Path.home()), "~").replace("@", " at ")


def write_evidence(path: Path, case: str, meeting_id: str, code: int) -> None:
    result = {0: "summarised", 1: "failed"}.get(code, "timed out or no answer")
    block = [
        f"## {case}: `{meeting_id}`",
        "",
        f"- Checked {datetime.now(UTC):%Y-%m-%d %H:%M} UTC through GET /api/meetings/{meeting_id}; result: {result}",
        "",
        *[f"    {mask(line)}" for line in LINES],
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", encoding="utf-8") as fh:
        if new:
            fh.write("# M2: meeting jobs through the Functions host on the laptop\n\n")
        fh.write("\n".join(block) + "\n")
    print(f"appended to {path}")


def fetch(url: str, meeting_id: str) -> tuple[int, dict]:
    request = urllib.request.Request(f"{url.rstrip('/')}/api/meetings/{meeting_id}")  # noqa: S310
    if key := os.getenv("FUNCTION_KEY"):
        request.add_header("x-functions-key", key)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 (operator-given URL)
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return 0, {}


def stage_line(job: dict, stage: str) -> str:
    if stage == "received":
        docs = [f["document"] for f in job["files"] if f.get("document")]
        read = f", attachments read: {sum(d['blocks'] for d in docs)} block(s)" if docs else ""  # D22
        return f"{len(job['files'])} file(s), {job['recording_seconds']:.1f} s of audio{read}"
    if stage == "transcribed":
        t = job["transcript"]
        return (
            f"{t['segments']} segments, {t['audio_seconds']:.1f} s of audio in {t['seconds']:.1f} s "
            f"({t['engine']}; transcriptions: {job['stt_runs']})"
        )
    if stage == "summarised":
        m = job["summary_meta"]
        parts = f", {m['parts']} parts + merge" if m.get("parts", 1) > 1 else ""  # D24
        return f"{m['model']}, {m['seconds']:.1f} s, {m['completion_tokens']} completion tokens{parts}"
    e = job["error"]
    return f"{e['code']} at {e['stage']}: {e['message']}{' (retryable)' if e['retryable'] else ''}"


def report(job: dict, printed: set[str]) -> None:
    order = sorted(job["stages"].items(), key=lambda kv: kv[1])
    for stage, _ in order:
        if stage not in printed:
            printed.add(stage)
            say(f"{job['id']}  {stage:<12} {stage_line(job, stage)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("meeting_id")
    parser.add_argument("--url", default="http://127.0.0.1:7071")
    parser.add_argument("--wait", type=float, default=0, metavar="SECONDS")
    parser.add_argument("--until", choices=["received", "transcribed"], help="stop once this stage is reached")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--evidence", type=Path, help="append the output to this markdown file")
    parser.add_argument("--case", default="run", help="heading for the evidence block")
    args = parser.parse_args()
    code = follow(args)
    if args.evidence and code in (0, 1):
        write_evidence(args.evidence, args.case, args.meeting_id, code)
    elif args.evidence:
        print(f"nothing appended to {args.evidence}: no final state was read")
    return code


def follow(args) -> int:

    deadline, printed, said_waiting, said_silent = time.monotonic() + args.wait, set(), False, False
    while True:
        status, job = fetch(args.url, args.meeting_id)
        if status == 200:
            if args.json:
                print(json.dumps(job, indent=2, ensure_ascii=False))
                return 0
            report(job, printed)
            if args.until and args.until in job["stages"]:
                return 0
            if job["stage"] in TERMINAL:
                break
        elif status == 0 and not args.wait:
            print(f"FAIL no answer from {args.url}: is the Functions host running (cd src && func start)?")
            return 2
        elif status == 0:  # a busy or restarting host: keep asking until the deadline (M2 run A)
            if not said_silent:
                print(f"{args.meeting_id}  no answer from {args.url} (host busy or down), still asking", flush=True)
                said_silent = True
        elif status != 404:
            print(f"FAIL HTTP {status}: {job.get('error', '')}")
            return 2
        elif not said_waiting:
            say(f"{args.meeting_id}  no job yet" + (" (waiting)" if args.wait else ""))
            said_waiting = True
        if time.monotonic() >= deadline:
            if args.wait:
                say(f"TIMEOUT after {args.wait:.0f} s")
                return 2
            return 0 if status == 200 else 1
        time.sleep(2)

    say(
        f"{job['id']}  attempts {job['attempts']}, deliveries {job['deliveries']}, "
        f"ignored uploads {job['ignored_uploads']}, earlier errors {len(job['history'])}"
    )
    if job["stage"] == "summarised":
        for line in show(MeetingSummary.model_validate(job["summary"])):
            say(line)
        for warning in job["summary_meta"]["grounding_warnings"]:
            say(f"grounding   {warning}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
