"""The evaluation (D26): every meeting of a set through speech to text and the summary, scored against its answers.

uv run python scripts/eval_meetings.py --set tuning [--only M04] [--fresh-stt]
uv run python scripts/eval_meetings.py --set holdout
uv run python scripts/eval_meetings.py --compare out/eval/tuning-phi4-mini-3.8b.json out/eval/tuning-granite4-3b.json

Sets are in eval/sets.json: scripted meetings (eval/meetings/<ID>.json; audio from scripts/make_meeting.py) and AMI
meetings (ami:<ID>; eval/ami/<ID>.json and data/ami/<ID>.wav from scripts/ami_set.py). Transcripts are made once
per meeting and speech model and kept in out/eval/transcripts/ (--fresh-stt makes them again), so comparing chat
models (CHAT_MODEL=...) runs only the summaries. Writes out/eval/<set>-<model>.json and
docs/evidence/m3-eval-<set>-<model>.md.

The gates (meeting.evaluate.gates) apply to the scripted meetings of the tuning set. The AMI meetings are scored
and reported, not gated: their answers were written by the corpus annotators for their own summaries, not for
this contract, and matching them takes words, not keywords. The holdout set is reported only and never tuned
against (D26): a change made because of a holdout result needs a new holdout first.
"""

import argparse
import json
import re
import sys
import time
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import openai
from summarize_file import cpu_model, show

from meeting.documents import LocalReader
from meeting.evaluate import KINDS, Score, gates, score
from meeting.expect import wer
from meeting.llm import JsonModel
from meeting.media import attachment_kind
from meeting.settings import load
from meeting.summarize import SummaryInvalid, summarize
from meeting.transcript import Transcript

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "eval"
EVIDENCE = ROOT / "docs" / "evidence"


def slug(model: str) -> str:
    return re.sub(r"[^a-z0-9.]+", "-", model.casefold()).strip("-")


def load_meeting(entry: str) -> dict:
    """One set entry as {id, kind, title, attendees, audio, answers, timings, script, attachments}."""
    if entry.startswith("ami:"):
        meeting_id = entry.removeprefix("ami:")
        path = ROOT / "eval" / "ami" / f"{meeting_id}.json"
        if not path.is_file():
            raise SystemExit(f"{path.relative_to(ROOT)} is missing: run uv run python scripts/ami_set.py fetch")
        doc = json.loads(path.read_text(encoding="utf-8"))
        return {
            "id": meeting_id,
            "kind": "corpus",
            "title": doc["title"],
            "attendees": (),
            "audio": ROOT / "data" / "ami" / f"{meeting_id}.wav",
            "answers": doc["answers"],
            "timings": None,
            "script": None,
            "attachments": [],
        }
    doc = json.loads((ROOT / "eval" / "meetings" / f"{entry}.json").read_text(encoding="utf-8"))
    timings = ROOT / "out" / "meetings" / f"{entry}.lines.json"
    return {
        "id": entry,
        "kind": "script",
        "title": doc["title"],
        "attendees": tuple(doc["speakers"]),
        "audio": ROOT / "out" / "meetings" / f"{entry}.wav",
        "answers": doc["answers"],
        "timings": json.loads(timings.read_text()) if timings.is_file() else None,
        "script": " ".join(text for _, text in doc["lines"]),
        "attachments": [ROOT / "out" / "meetings" / entry / a["name"] for a in doc.get("attachments", [])],
    }


def transcript_for(meeting: dict, settings, fresh: bool, transcriber: list) -> Transcript:
    cache = OUT / "transcripts" / f"{meeting['id']}.{settings.stt_model}.json"
    if cache.is_file() and not fresh:
        return Transcript.read(cache)
    if not meeting["audio"].is_file():
        hint = "scripts/ami_set.py fetch" if meeting["kind"] == "corpus" else f"scripts/make_meeting.py {meeting['id']}"
        raise SystemExit(f"{meeting['audio'].relative_to(ROOT)} is missing: run uv run python {hint}")
    if not transcriber:
        from meeting.stt import WhisperTranscriber

        transcriber.append(WhisperTranscriber.from_settings(settings))
    transcript = transcriber[0].transcribe(meeting["audio"], names=meeting["attendees"])
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(transcript.to_json(), encoding="utf-8")
    return transcript


def documents_for(meeting: dict, reader: LocalReader) -> tuple:
    docs = []
    for path in meeting["attachments"]:
        if not path.is_file():
            raise SystemExit(
                f"{path.relative_to(ROOT)} is missing: run uv run python scripts/make_meeting.py {meeting['id']}"
            )
        kind = attachment_kind(path.read_bytes()[:64], path.name)
        docs.append(reader.read(path, path.name, kind))
    return tuple(docs)


def kind_cells(s: Score) -> list[str]:
    return [f"{s.kinds[k].matched}/{s.kinds[k].expected} of {s.kinds[k].found}" for k in KINDS]


def pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def totals_rows(name: str, total: Score) -> list[str]:
    k = total.kinds
    return [
        f"| {name} | "
        + " | ".join(f"{pct(k[x].recall)} / {pct(k[x].precision)}" for x in KINDS)
        + f" | {pct(total.owner.rate)} | {pct(total.due.rate)} | {pct(total.evidence.rate)} | {pct(total.source.rate)}"
        + f" | {sum(x.invented_in_empty for x in k.values())} | {total.forbidden} | {total.confusions} |"
    ]


def run(args) -> int:
    settings = load()
    sets = json.loads((ROOT / "eval" / "sets.json").read_text())
    entries = [e for e in sets[args.set] if not args.only or e.removeprefix("ami:") in args.only]
    meetings = [load_meeting(e) for e in entries]  # every input checked before the first long step
    for m in meetings:
        cached = (OUT / "transcripts" / f"{m['id']}.{settings.stt_model}.json").is_file() and not args.fresh_stt
        hint = "scripts/ami_set.py fetch" if m["kind"] == "corpus" else f"scripts/make_meeting.py {m['id']}"
        for path in [] if cached else [m["audio"]]:
            if not path.is_file():
                raise SystemExit(f"{path.relative_to(ROOT)} is missing: run uv run python {hint}")
        for path in m["attachments"]:
            if not path.is_file():
                raise SystemExit(f"{path.relative_to(ROOT)} is missing: run uv run python {hint}")
    model = JsonModel.from_settings(settings)
    reader = LocalReader(max_pages=settings.max_attachment_pages)
    transcriber: list = []
    rows, details, results = [], [], []
    totals = {"script": Score(), "corpus": Score()}
    counts = {"script": [0, 0], "corpus": [0, 0]}  # meetings, valid summaries
    started = time.perf_counter()
    for meeting in meetings:
        transcript = transcript_for(meeting, settings, args.fresh_stt, transcriber)
        documents = documents_for(meeting, reader)
        heard = wer(meeting["script"], transcript.text) if meeting["script"] else None
        counts[meeting["kind"]][0] += 1
        try:
            result = summarize(
                transcript,
                model,
                attendees=meeting["attendees"],
                documents=documents,
                max_chars=settings.transcript_max_chars,
                part_chars=settings.part_max_chars,
                attachment_chars=settings.attachment_context_chars,
            )
        except SummaryInvalid as exc:
            print(f"{meeting['id']:8} INVALID {exc}")
            rows.append(f"| {meeting['id']} | {meeting['kind']} | invalid: {exc} | | | | | | | | |")
            results.append({"id": meeting["id"], "kind": meeting["kind"], "valid": False, "error": str(exc)})
            continue
        except openai.APIConnectionError:
            print(f"FAIL no answer from {settings.openai_base_url}: is Ollama up? (docker compose --profile ai up -d)")
            return 2
        except openai.NotFoundError as exc:
            print(f"FAIL {settings.chat_model} is not available at {settings.openai_base_url}: {exc.message}")
            return 2
        counts[meeting["kind"]][1] += 1
        s = score(result.summary, meeting["answers"], meeting["timings"])
        totals[meeting["kind"]].add(s)
        c = result.completion
        target = OUT / slug(settings.chat_model) / f"{meeting['id']}.summary.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.summary.model_dump_json(indent=2) + "\n", encoding="utf-8")
        minutes = transcript.audio_seconds / 60
        cells = kind_cells(s)
        print(
            f"{meeting['id']:8} {minutes:4.1f} min  parts {result.parts}  {c.seconds:6.1f} s  "
            f"decisions {cells[0]}  actions {cells[1]}  questions {cells[2]}"
            + (f"  forbidden {s.forbidden}" if s.forbidden else "")
        )
        rows.append(
            f"| {meeting['id']} | {meeting['kind']} | {minutes:.1f} | {pct(heard)} | {result.parts} "
            + f"| {c.seconds:.0f} | "
            + " | ".join(cells)
            + f" | {s.forbidden} | {s.confusions} |"
        )
        missing = [
            f"- missing {kind[:-1].replace('_', ' ')}: {json.dumps(meeting['answers'][kind][i], ensure_ascii=False)}"
            for kind in KINDS
            for i in s.kinds[kind].missing
        ]
        details += [
            f"### {meeting['id']}: {meeting['title']}",
            "",
            *[f"    {line}" for line in show(result.summary)],
            "",
            *missing,
            *[f"- {note}" for note in s.notes],
            *[f"- grounding: {w}" for w in result.warnings],
            "",
        ]
        results.append(
            {
                "id": meeting["id"],
                "kind": meeting["kind"],
                "valid": True,
                "minutes": round(minutes, 2),
                "wer": heard,
                "parts": result.parts,
                "seconds": c.seconds,
                "completion_tokens": c.completion_tokens,
                "kinds": {k: vars(v) for k, v in s.kinds.items()},
                "owner": vars(s.owner),
                "due": vars(s.due),
                "evidence": vars(s.evidence),
                "source": vars(s.source),
                "forbidden": s.forbidden,
                "confusions": s.confusions,
            }
        )

    checks = gates(totals["script"], *counts["script"]) if args.set == "tuning" and not args.only else []
    passed = all(g.passed for g in checks)
    elapsed = time.perf_counter() - started
    name = f"{args.set}-{slug(settings.chat_model)}"
    machine = {
        "set": args.set,
        "model": settings.chat_model,
        "date": f"{datetime.now(UTC):%Y-%m-%d %H:%M} UTC",
        "part_max_chars": settings.part_max_chars,
        "meetings": results,
        "totals": {g: {"kinds": {k: vars(v) for k, v in t.kinds.items()}} for g, t in totals.items()},
        "gates": [{"name": g.name, "value": g.value, "limit": g.limit, "passed": g.passed} for g in checks],
        "passed": passed if checks else None,
        "seconds": round(elapsed, 1),
    }

    header = "| Meeting | Kind | Minutes | WER | Parts | Summary s | Decisions | Actions | Questions "
    header += "| Forbidden | Confused |"
    lines = [
        f"# M3 evaluation: {args.set} set, {settings.chat_model}",
        "",
        f"- Date: {machine['date']}",
        f"- Machine: {cpu_model()}, {settings.stt_threads} threads for speech to text",
        f"- Speech to text: {settings.stt_model} ({settings.stt_mode}), faster-whisper {version('faster-whisper')}",
        f"- Summary: {settings.chat_model}, parts of at most {settings.part_max_chars} characters, attachments "
        f"{settings.attachment_context_chars} characters, openai {version('openai')}",
        f"- {len(results)} meetings in {elapsed / 60:.1f} min (transcripts cached in out/eval/transcripts/ count as 0)",
        "- Cells: matched / expected of found. Scripted meetings use keyword answers (D26); AMI meetings use the "
        "annotators' sentences (CC BY 4.0), matched by words, reported and not gated.",
        "",
        header,
        "|" + "---|" * (header.count("|") - 1),
        *rows,
        "",
        "## Totals (recall / precision per kind; detail rates on matched items)",
        "",
        "| Group | Decisions | Actions | Questions | Owner | Due | Evidence | Source | Invented | Forbidden "
        "| Confused |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
        *totals_rows("scripted", totals["script"]),
        *(totals_rows("AMI", totals["corpus"]) if counts["corpus"][0] else []),
        "",
    ]
    if checks:
        lines += ["## Gates (scripted meetings of the tuning set)", "", *[f"- {g.line()}" for g in checks], ""]
        lines += [f"**{'PASSED' if passed else 'FAILED'}**", ""]
    else:
        lines += ["Reported only: the holdout set is never tuned against (D26).", ""]
    lines += ["## Summaries", "", *details]
    evidence = EVIDENCE / f"m3-eval-{name}.md"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines).replace("@", " at ")
    if not args.only:  # a partial run is for looking, not for evidence or a comparison
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"{name}.json").write_text(json.dumps(machine, indent=2) + "\n", encoding="utf-8")
        evidence.write_text(text, encoding="utf-8")
        print(f"wrote out/eval/{name}.json, {evidence.relative_to(ROOT)}")
    for g in checks:
        print(g.line())
    if checks:
        print("EVAL PASSED" if passed else "EVAL FAILED")
    else:
        print("EVAL REPORTED (not gated: " + ("a partial run)" if args.only else "the holdout set)"))
    return 0 if passed or not checks else 1


def compare(paths: list[Path]) -> int:
    runs = [json.loads(p.read_text()) for p in paths]
    rows = []
    for r in runs:
        t = r["totals"]["script"]["kinds"]

        def rate(kind, what, t=t):
            k = t[kind]
            denominator = k["expected"] if what == "recall" else k["found"]
            return pct(k["matched"] / denominator if denominator else None)

        corpus = r["totals"]["corpus"]["kinds"]

        def ami(kind, corpus=corpus):
            k = corpus[kind]
            return pct(k["matched"] / k["expected"] if k["expected"] else None)

        valid = [m for m in r["meetings"] if m["valid"]]
        seconds = sum(m["seconds"] for m in valid)
        failed = [g["name"] for g in r["gates"] if not g["passed"]]
        rows.append(
            f"| {r['model']} | {len(valid)}/{len(r['meetings'])} | "
            + " | ".join(f"{rate(k, 'recall')} / {rate(k, 'precision')}" for k in KINDS)
            + f" | {ami('decisions')} / {ami('action_items')} | {seconds / 60:.1f} | "
            + f"{'PASSED' if r['passed'] else 'FAILED: ' + ', '.join(failed)} |"
        )
    lines = [
        "# M3: local chat models on the tuning set",
        "",
        f"- Compared on {datetime.now(UTC):%Y-%m-%d} from " + ", ".join(f"`out/eval/{p.name}`" for p in paths),
        "- Recall / precision on the scripted meetings; summary minutes for every meeting of the set, same machine,"
        " same cached transcripts.",
        "",
        "| Model | Valid | Decisions | Actions | Questions | AMI recall (decisions / actions) | Summary min | Gates |",
        "|---|---|---|---|---|---|---|---|",
        *rows,
        "",
    ]
    target = EVIDENCE / "m3-models.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(rows))
    print(f"wrote {target.relative_to(ROOT)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set", choices=["tuning", "holdout"], default="tuning")
    parser.add_argument("--only", nargs="+", metavar="ID", help="only these meetings (no evidence file)")
    parser.add_argument("--fresh-stt", action="store_true", help="transcribe again instead of using the cache")
    parser.add_argument("--compare", nargs="+", type=Path, metavar="JSON", help="compare earlier runs")
    args = parser.parse_args()
    return compare(args.compare) if args.compare else run(args)


if __name__ == "__main__":
    sys.exit(main())
