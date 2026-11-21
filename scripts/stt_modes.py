"""Whisper's two ways through a long recording, on the same script spoken with several seeds (D13).

uv run python scripts/stt_modes.py M01 [--seeds 5] [--out docs/evidence/m1-stt-modes.md]

For each seed: make the meeting (scripts/make_meeting.py's render), transcribe it in `sequential` mode (Whisper's
own 30-second sliding window) and in `batched` mode (pieces cut at pauses, each transcribed on its own), and score
both against the script. A run of WER far above the rest is the sliding window skipping ahead (lines missing from
the transcript), not a misheard word or two. About 30 s per seed on 2 slow cores.
"""

import argparse
import dataclasses
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from make_meeting import read_meeting, render, write_wav

from meeting.expect import MAX_WER, wer
from meeting.settings import load
from meeting.stt import WhisperTranscriber

MODES = ("sequential", "batched")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("meeting", metavar="ID")
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--out", type=Path, help="also write the table as a markdown evidence file")
    args = parser.parse_args()

    settings = load()
    meeting = read_meeting(args.meeting)
    script = " ".join(text for _, text in meeting["lines"])
    names = tuple(meeting["speakers"])
    transcribers = {m: WhisperTranscriber.from_settings(dataclasses.replace(settings, stt_mode=m)) for m in MODES}

    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{args.meeting}.wav"
        for seed in range(args.seeds):
            frames, rate = render(meeting, settings.models_dir, seed)
            write_wav(audio, frames, rate)
            row = {"seed": seed, "audio": len(frames) / 2 / rate}
            for mode, transcriber in transcribers.items():
                transcript = transcriber.transcribe(audio, names=names)
                row[mode] = (wer(script, transcript.text), len(transcript.segments), transcript.seconds)
            rows.append(row)
            print(
                f"seed {seed}  audio {row['audio']:5.1f} s  "
                + "  ".join(f"{m} WER {row[m][0]:6.1%} ({row[m][1]:2d} segments, {row[m][2]:5.1f} s)" for m in MODES),
                flush=True,
            )

    over = {m: sum(r[m][0] > MAX_WER for r in rows) for m in MODES}
    summary = [f"{m}: {over[m]} of {len(rows)} runs above {MAX_WER:.0%} WER" for m in MODES]
    print("\n".join(summary))

    if args.out:
        lines = [
            f"# M1: Whisper sequential vs batched on {args.meeting} ({len(meeting['lines'])} lines)",
            "",
            f"- Date: {datetime.now(UTC):%Y-%m-%d %H:%M} UTC",
            f"- {settings.stt_model}, int8, beam {settings.stt_beam_size}, {settings.stt_threads} threads, "
            f"batch size {settings.stt_batch_size}, voice-activity filter on, attendees as hotwords",
            "- Same script, Piper seeds 0 to N-1: the audio differs slightly per seed, the words do not.",
            "",
            "| Seed | Audio s | " + " | ".join(f"{m} WER | {m} segments | {m} s" for m in MODES) + " |",
            "|---|---|" + "---|---|---|" * len(MODES),
        ]
        for r in rows:
            cells = " | ".join(f"{r[m][0]:.1%} | {r[m][1]} | {r[m][2]:.1f}" for m in MODES)
            lines.append(f"| {r['seed']} | {r['audio']:.1f} | {cells} |")
        lines += ["", *[f"- {line}" for line in summary], ""]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("\n".join(lines), encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
