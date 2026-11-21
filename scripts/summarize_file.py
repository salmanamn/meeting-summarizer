"""One recording through the whole pipeline in this process (M1): audio -> transcript -> summary.

uv run python scripts/summarize_file.py out/meetings/M01.wav --expect M01 [--evidence docs/evidence/m1-M01.md]
uv run python scripts/summarize_file.py --transcript out/M01.transcript.json --expect M01   skip speech to text
uv run python scripts/summarize_file.py out/meetings/M01.wav --stt-only                     transcript only

Writes out/<name>.transcript.json and out/<name>.summary.json. --expect compares with eval/meetings/<ID>.json (D7):
transcript against the script, summary against the script's `expect` block; exit 1 when a check fails.
"""

import argparse
import json
import platform
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import openai

from meeting.expect import check, wer
from meeting.llm import JsonModel
from meeting.settings import load
from meeting.stt import WhisperTranscriber
from meeting.summarize import NoSpeech, SummaryInvalid, TranscriptTooLong, summarize
from meeting.transcript import Transcript

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"


def cpu_model() -> str:
    """The CPU's name, without the '@' Intel puts before the clock speed: evidence files carry no '@' at all."""
    for line in Path("/proc/cpuinfo").read_text().splitlines():
        if line.startswith("model name"):
            return " ".join(line.split(":", 1)[1].replace("@", "at").split())
    return platform.processor() or "unknown CPU"


def show(summary) -> list[str]:
    lines = [f"title     {summary.title}", f"overview  {summary.overview}"]
    for d in summary.decisions:
        lines.append(f"decision  [{d.evidence or '--:--'}] {d.text}")
    for a in summary.action_items:
        due = f" (due: {a.due})" if a.due else ""
        lines.append(f"action    [{a.evidence or '--:--'}] {a.owner or '(no owner)'}: {a.task}{due}")
    for q in summary.open_questions:
        lines.append(f"question  [{q.evidence or '--:--'}] {q.question}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("audio", nargs="?", type=Path, help="a recording (any format FFmpeg reads)")
    source.add_argument("--transcript", type=Path, help="a transcript JSON written by an earlier run")
    parser.add_argument("--expect", metavar="ID", help="check against eval/meetings/<ID>.json")
    parser.add_argument(
        "--attendees",
        help="comma-separated names (default with --expect: the script's speakers); hints for both models",
    )
    parser.add_argument("--stt-only", action="store_true", help="stop after the transcript")
    parser.add_argument("--evidence", type=Path, help="also write the run as a markdown evidence file")
    args = parser.parse_args()

    settings = load()
    OUT.mkdir(exist_ok=True)
    meeting = None
    if args.expect:
        meeting = json.loads((ROOT / "eval" / "meetings" / f"{args.expect}.json").read_text(encoding="utf-8"))
    if args.attendees is not None:
        attendees = tuple(n.strip() for n in args.attendees.split(",") if n.strip())
    else:
        attendees = tuple(meeting["speakers"]) if meeting else ()

    if args.transcript:
        transcript = Transcript.read(args.transcript)
        name = args.transcript.name.removesuffix(".transcript.json")
    else:
        name = args.audio.stem
        transcript = WhisperTranscriber.from_settings(settings).transcribe(args.audio, names=attendees)
        (OUT / f"{name}.transcript.json").write_text(transcript.to_json(), encoding="utf-8")
    print(
        f"transcript  {len(transcript.segments)} segments, {len(transcript.text.split())} words, "
        f"language {transcript.language}, {transcript.audio_seconds:.1f} s of audio in {transcript.seconds:.1f} s "
        f"(RTF {transcript.rtf:.2f}, {transcript.engine}, {settings.stt_threads} threads)"
    )

    transcript_wer = None
    if meeting:
        transcript_wer = wer(" ".join(text for _, text in meeting["lines"]), transcript.text)
        print(f"transcript  WER {transcript_wer:.1%} against the script of {args.expect}")
    if args.stt_only:
        print(transcript.timestamped())
        return 0

    model = JsonModel.from_settings(settings)
    try:
        result = summarize(transcript, model, attendees=attendees, max_chars=settings.transcript_max_chars)
    except (NoSpeech, TranscriptTooLong, SummaryInvalid) as exc:
        print(f"FAIL {type(exc).__name__}: {exc}")
        return 1
    except openai.APIConnectionError:
        print(f"FAIL no answer from {settings.openai_base_url}: is Ollama up? (docker compose --profile ai up -d)")
        return 2
    except openai.NotFoundError as exc:
        print(f"FAIL {settings.chat_model} is not available at {settings.openai_base_url}: {exc.message}")
        return 2
    c = result.completion
    (OUT / f"{name}.summary.json").write_text(result.summary.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(
        f"summary     {c.seconds:.1f} s, {c.prompt_tokens} prompt + {c.completion_tokens} completion tokens, "
        f"{settings.chat_model}; written to out/{name}.summary.json"
    )
    summary_lines = show(result.summary)
    print("\n".join(summary_lines))
    for warning in result.warnings:
        print(f"grounding   {warning}")

    checks = check(result.summary, meeting["expect"], transcript_wer=transcript_wer) if meeting else []
    for item in checks:
        print(f"{'OK  ' if item.passed else 'FAIL'} {item.label}")
    passed = all(item.passed for item in checks)
    if meeting:
        print("CHECK PASSED" if passed else "CHECK FAILED")

    if args.evidence:
        lines = [
            f"# M1: {name} through the pipeline on the laptop",
            "",
            f"- Date: {datetime.now(UTC):%Y-%m-%d %H:%M} UTC",
            f"- Machine: {cpu_model()}, {settings.stt_threads} threads for speech to text",
            f"- Speech to text: {transcript.engine}, compute type {settings.stt_compute_type}, beam "
            f"{settings.stt_beam_size}, language {transcript.language}, faster-whisper {version('faster-whisper')}",
            f"- Attendees given as hints: {', '.join(attendees) or 'none'}",
            f"- Summary: {settings.chat_model} at {settings.openai_base_url}, openai {version('openai')}",
            f"- Transcript: {len(transcript.segments)} segments, {transcript.audio_seconds:.1f} s of audio in "
            f"{transcript.seconds:.1f} s (RTF {transcript.rtf:.2f})"
            + (f", WER {transcript_wer:.1%} against the script" if transcript_wer is not None else ""),
            f"- Summary call: {c.seconds:.1f} s, {c.prompt_tokens} prompt + {c.completion_tokens} completion tokens",
            "- Synthetic meeting from a script (D7): this checks the pipeline, not quality on real recordings.",
            "",
            "## Summary",
            "",
            *[f"    {line}" for line in summary_lines],
            "",
            "## Grounding corrections",
            "",
            *([f"- {w}" for w in result.warnings] or ["- none"]),
            "",
        ]
        if checks:
            lines += ["## Checks", "", *[f"- {'OK' if i.passed else 'FAIL'}: {i.label}" for i in checks], ""]
            lines += [f"**{'PASSED' if passed else 'FAILED'}**", ""]
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text("\n".join(lines), encoding="utf-8")
        print(f"wrote {args.evidence}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
