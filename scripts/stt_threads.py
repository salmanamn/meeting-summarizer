"""How many CPU threads Whisper should get on this machine (STT_THREADS, open since M1).

uv run python scripts/stt_threads.py out/meetings/M01.wav [--threads 2,4,8] [--runs 2] [--out <file.md>]

M1's laptop run took 29.8 s with 8 threads where the 2-vCPU sandbox took 11.5 s with 2: more threads than
physical cores (hyper-threads) can make CTranslate2 slower. Each setting transcribes the same file `--runs`
times with a freshly loaded model; the table has the fastest and the slowest run per setting. The words do not
depend on the thread count, so the WER column (against the script, with --expect) only proves nothing broke.
--apply src/local.settings.json.example writes the fastest setting there (the Functions host reads it from
local.settings.json, which is copied from the example).
"""

import argparse
import dataclasses
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from summarize_file import cpu_model

from meeting.expect import wer
from meeting.settings import load
from meeting.stt import WhisperTranscriber

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--threads", default="2,4,8")
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--expect", metavar="ID", default="M01")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--apply", type=Path, metavar="SETTINGS_JSON", help="write the fastest into its STT_THREADS")
    args = parser.parse_args()

    settings = load()
    meeting = json.loads((ROOT / "eval" / "meetings" / f"{args.expect}.json").read_text(encoding="utf-8"))
    script = " ".join(text for _, text in meeting["lines"])
    names = tuple(meeting["speakers"])
    rows = []
    for threads in (int(t) for t in args.threads.split(",")):
        transcriber = WhisperTranscriber.from_settings(dataclasses.replace(settings, stt_threads=threads))
        times, error = [], 0.0
        for _ in range(args.runs):
            transcript = transcriber.transcribe(args.audio, names=names)
            times.append(transcript.seconds)
            error = wer(script, transcript.text)
        rows.append((threads, min(times), max(times), transcript.audio_seconds, error))
        print(
            f"threads {threads}: {min(times):5.1f}-{max(times):5.1f} s "
            f"for {transcript.audio_seconds:.1f} s of audio, WER {error:.1%}",
            flush=True,
        )
    best = min(rows, key=lambda r: r[1])
    print(f"fastest: {best[0]} threads")
    if args.apply:
        data = json.loads(args.apply.read_text(encoding="utf-8"))
        data["Values"]["STT_THREADS"] = str(best[0])
        args.apply.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"STT_THREADS={best[0]} written to {args.apply}")

    if args.out:
        lines = [
            f"# M2: Whisper threads on {args.audio.name}",
            "",
            f"- Date: {datetime.now(UTC):%Y-%m-%d %H:%M} UTC",
            f"- Machine: {cpu_model()}, {os.cpu_count()} logical CPUs",
            f"- {settings.stt_model}, {settings.stt_mode}, int8, beam {settings.stt_beam_size}, "
            f"{args.runs} run(s) per setting",
            "",
            "| Threads | Fastest s | Slowest s | Audio s | RTF (fastest) | WER |",
            "|---|---|---|---|---|---|",
            *[f"| {t} | {lo:.1f} | {hi:.1f} | {a:.1f} | {lo / a:.2f} | {e:.1%} |" for t, lo, hi, a, e in rows],
            "",
            f"- Fastest: {best[0]} threads.",
            "",
        ]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("\n".join(lines), encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
