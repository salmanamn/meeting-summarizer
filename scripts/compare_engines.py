"""Speech against Whisper on one scripted meeting (M7, D50): the transcripts, and summaries made by one chat model.

uv run python scripts/compare_engines.py M01 --azure-id m7-m01-1 --out docs/evidence/m7-compare-M01.md
uv run python scripts/compare_engines.py M01 --azure-id m7-m01-1 --whisper out/M01.whisper.transcript.json

Needs the deployed stack's laptop settings in the environment (`source ~/meet-azure.env`, written by
scripts/azure_env.sh): the job record is read from Cosmos DB and the Speech transcript from transcripts/ as you
(az login, the operator's read roles, D49); the two laptop summaries are made by the stack's own chat deployment
(the operator's Cognitive Services OpenAI User role), so only the transcript differs between them.

Three summaries of the same recording:
  azure            the deployed job: Speech batch transcription, then the chat model in the Function
  laptop/speech    the job's Speech transcript, summarised again from the laptop with the same deployment
  laptop/whisper   Whisper (stt-small, attendee names as hotwords) on the laptop, summarised with the same deployment
The first two differ only in the model's own variation; the last two only in the transcriber. Every summary is
scored against the meeting's answers (eval/meetings/<ID>.json) like scripts/summarize_file.py does, and each
transcript against the script (WER). Writes out/<azure-id>.speech.transcript.json, out/<ID>.whisper.transcript.json
(unless --whisper is given) and, with --out, a markdown evidence file with no '@' and no home directory in it.

Exit 0 when the comparison was written (whatever the checks say), 1 when the Azure job isn't summarised, 2 when a
needed setting or file is missing.
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from summarize_file import show

from meeting.evaluate import meeting_checks, score
from meeting.expect import wer
from meeting.summary import MeetingSummary
from meeting.transcript import Transcript
from meeting.words import normalize

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
EXCERPT_LINES = 8  # transcript lines shown per engine: enough to see speaker labels and how names came out


@dataclass
class Run:
    label: str
    transcript: str  # which transcript it summarised (a label of the transcripts table)
    model: str
    summary: MeetingSummary
    checks: list[tuple[str, bool]]
    warnings: list[str] = field(default_factory=list)
    seconds: float | None = None
    completion_tokens: int | None = None


def mask(text: str) -> str:
    """Evidence carries no '@' and no home directory (the handoff's rule: mask in the command that writes it)."""
    return text.replace(str(Path.home()), "~").replace("@", " at ")


def split_blob(path: str) -> tuple[str, str]:
    """'transcripts/<meeting>/<sha16>.azure-speech.json' -> ('transcripts', '<meeting>/<sha16>.azure-speech.json')."""
    container, _, name = path.partition("/")
    if not container or not name:
        raise ValueError(f"not a <container>/<blob> path: {path!r}")
    return container, name


def speakers(transcript: Transcript) -> list[str]:
    """Diarization labels in order of first appearance (Speech: Guest-1, Guest-2, ...; Whisper: none)."""
    seen: list[str] = []
    for segment in transcript.segments:
        if segment.speaker and segment.speaker not in seen:
            seen.append(segment.speaker)
    return seen


def names_heard(transcript: Transcript, attendees: list[str]) -> list[str]:
    """Attendee names that appear as words in the transcript, spelled as on the list (D44: Speech gets no hints)."""
    words = set(normalize(transcript.text))
    return [name for name in attendees if set(normalize(name)) <= words]


def reference_text(meeting: dict) -> str:
    return " ".join(text for _, text in meeting["lines"])


def checks_for(summary: MeetingSummary, meeting: dict, timings: list[dict] | None, transcript_wer: float):
    return meeting_checks(score(summary, meeting["answers"], timings), transcript_wer)


def passed(checks: list[tuple[str, bool]]) -> str:
    return f"{sum(ok for _, ok in checks)} of {len(checks)}"


def owners(summary: MeetingSummary) -> str:
    return ", ".join(a.owner or "(none)" for a in summary.action_items) or "-"


def transcript_rows(transcripts: dict[str, Transcript], meeting: dict) -> list[str]:
    attendees, script_speakers = list(meeting["speakers"]), len(meeting["speakers"])
    rows = [
        "| Transcript | Engine | Segments | Words | Audio s | Took s | WER vs script | Speakers found | Names heard |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for label, t in transcripts.items():
        found = speakers(t)
        heard = names_heard(t, attendees)
        rows.append(
            f"| {label} | {t.engine} | {len(t.segments)} | {len(t.text.split())} | {t.audio_seconds:.1f} | "
            f"{t.seconds:.1f} | {wer(reference_text(meeting), t.text):.1%} | "
            f"{len(found) if found else 'none'} (script: {script_speakers}) | "
            f"{len(heard)} of {len(attendees)}{': ' + ', '.join(heard) if heard else ''} |"
        )
    return rows


def summary_rows(runs: list[Run]) -> list[str]:
    rows = [
        "| Summary | Transcript | Model | Decisions | Actions | Questions | Owners | Checks passed | Grounding fixes | "
        "Took s | Completion tokens |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in runs:
        s = r.summary
        rows.append(
            f"| {r.label} | {r.transcript} | {r.model} | {len(s.decisions)} | {len(s.action_items)} | "
            f"{len(s.open_questions)} | {owners(s)} | {passed(r.checks)} | {len(r.warnings)} | "
            f"{'-' if r.seconds is None else f'{r.seconds:.1f}'} | "
            f"{'-' if r.completion_tokens is None else r.completion_tokens} |"
        )
    return rows


def render(meeting: dict, azure_id: str, transcripts: dict[str, Transcript], runs: list[Run], when: datetime) -> str:
    lines = [
        f"# M7: Speech against Whisper on {meeting['id']} (Azure job `{azure_id}`)",
        "",
        f"- Compared {when:%Y-%m-%d %H:%M} UTC by scripts/compare_engines.py (D50). Synthetic meeting from a script "
        "(D7): one meeting is a smoke test of the comparison, not a quality ranking.",
        f"- Attendees on the manifest: {', '.join(meeting['speakers']) or 'none'}. Whisper got them as hotwords; "
        "Speech batch transcription takes no phrase list (D44).",
        "- `laptop/*` summaries use the stack's chat deployment from the laptop (D49), so `laptop/speech` against "
        "`laptop/whisper` differs only in the transcript; `azure` against `laptop/speech` only in the model's own "
        "variation.",
        "",
        "## Transcripts",
        "",
        *transcript_rows(transcripts, meeting),
        "",
        "## Summaries",
        "",
        *summary_rows(runs),
        "",
    ]
    for label, t in transcripts.items():
        lines += [f"### {label}: first {EXCERPT_LINES} lines", ""]
        lines += [f"    {line}" for line in t.timestamped().splitlines()[:EXCERPT_LINES]] + [""]
    for r in runs:
        lines += [f"### {r.label}", ""]
        lines += [f"    {line}" for line in show(r.summary)] + [""]
        lines += [f"- {'OK' if ok else 'FAIL'}: {label}" for label, ok in r.checks]
        lines += [f"- grounding: {w}" for w in r.warnings] + [""]
    return mask("\n".join(lines))


def azure_side(azure_id: str):
    """The job record (Cosmos, operator Data Reader) and its Speech transcript (transcripts/, operator Data Reader)."""
    from meeting.settings import load
    from meeting.stores import BlobStore, JobStore

    settings = load()
    if not settings.recordings_service_uri or settings.cosmos_key:
        raise SystemExit("FAIL no Azure settings in the environment: source ~/meet-azure.env (scripts/azure_env.sh)")
    record = JobStore.from_settings(settings).get(azure_id)
    if record is None:
        print(f"FAIL no job record {azure_id} in {settings.cosmos_endpoint}")
        raise SystemExit(1)
    if record.get("stage") != "summarised":
        print(f"FAIL job {azure_id} is at stage {record.get('stage')!r}, not summarised")
        raise SystemExit(1)
    container, name = split_blob(record["transcript"]["blob"])
    text = BlobStore.from_settings(settings).read_text(container, name)
    if text is None:
        print(f"FAIL {record['transcript']['blob']} is not readable")
        raise SystemExit(1)
    return record, Transcript.from_json(text)


def laptop_summary(
    label: str, transcript_label: str, transcript: Transcript, meeting: dict, timings, model, settings
) -> Run:
    """The job's own summarize() call (src/meeting/job.py), from the laptop, with the model the environment names."""
    from meeting.summarize import summarize

    result = summarize(
        transcript,
        model,
        attendees=tuple(meeting["speakers"]),
        max_chars=settings.transcript_max_chars,
        part_chars=settings.part_max_chars,
        attachment_chars=settings.attachment_context_chars,
    )
    return Run(
        label=label,
        transcript=transcript_label,
        model=settings.chat_model,
        summary=result.summary,
        checks=checks_for(result.summary, meeting, timings, wer(reference_text(meeting), transcript.text)),
        warnings=result.warnings,
        seconds=result.completion.seconds,
        completion_tokens=result.completion.completion_tokens,
    )


def whisper_transcript(meeting_id: str, meeting: dict, given: Path | None) -> Transcript:
    if given:
        return Transcript.read(given)
    from meeting.settings import load
    from meeting.stt import WhisperTranscriber

    audio = OUT / "meetings" / f"{meeting_id}.wav"
    if not audio.is_file():
        raise SystemExit(
            f"FAIL {audio.relative_to(ROOT)} is missing: uv run python scripts/make_meeting.py {meeting_id}"
        )
    settings = load()
    if settings.stt_engine != "whisper":
        raise SystemExit("FAIL the environment selects Speech (SPEECH_ENDPOINT or STT_ENGINE set): unset it")
    transcript = WhisperTranscriber.from_settings(settings).transcribe(audio, names=tuple(meeting["speakers"]))
    (OUT / f"{meeting_id}.whisper.transcript.json").write_text(transcript.to_json(), encoding="utf-8")
    return transcript


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("meeting", help="a scripted meeting id, e.g. M01 (eval/meetings/<ID>.json)")
    parser.add_argument("--azure-id", required=True, help="the meeting id the recording was uploaded under on Azure")
    parser.add_argument("--whisper", type=Path, help="a Whisper transcript from an earlier run (skips Whisper)")
    parser.add_argument("--out", type=Path, help="write the comparison as a markdown evidence file")
    args = parser.parse_args()

    path = ROOT / "eval" / "meetings" / f"{args.meeting}.json"
    if not path.is_file():
        print(f"FAIL {path.relative_to(ROOT)} does not exist")
        return 2
    meeting = json.loads(path.read_text(encoding="utf-8"))
    timings_file = OUT / "meetings" / f"{args.meeting}.lines.json"
    timings = json.loads(timings_file.read_text()) if timings_file.is_file() else None

    record, speech = azure_side(args.azure_id)
    OUT.mkdir(exist_ok=True)
    (OUT / f"{args.azure_id}.speech.transcript.json").write_text(speech.to_json(), encoding="utf-8")
    print(f"speech      {len(speech.segments)} segments, {len(speakers(speech))} speaker label(s), {speech.engine}")
    whisper = whisper_transcript(args.meeting, meeting, args.whisper)
    print(f"whisper     {len(whisper.segments)} segments, {whisper.engine}")

    from meeting.llm import JsonModel
    from meeting.settings import load

    settings = load()
    model = JsonModel.from_settings(settings)
    meta = record["summary_meta"]
    azure_summary = MeetingSummary.model_validate(record["summary"])
    runs = [
        Run(
            label="azure",
            transcript="speech",
            model=meta["model"],
            summary=azure_summary,
            checks=checks_for(azure_summary, meeting, timings, wer(reference_text(meeting), speech.text)),
            warnings=list(meta.get("grounding_warnings") or []),
            seconds=meta.get("seconds"),
            completion_tokens=meta.get("completion_tokens"),
        )
    ]
    for label, name, transcript in (("laptop/speech", "speech", speech), ("laptop/whisper", "whisper", whisper)):
        runs.append(laptop_summary(label, name, transcript, meeting, timings, model, settings))
        print(f"{label:<15} {passed(runs[-1].checks)} checks passed, owners: {owners(runs[-1].summary)}")

    report = render(meeting, args.azure_id, {"speech": speech, "whisper": whisper}, runs, datetime.now(UTC))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
