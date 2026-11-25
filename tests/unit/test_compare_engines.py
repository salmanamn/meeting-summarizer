"""scripts/compare_engines.py (M7, D50): what it measures and what it writes, without Azure."""

import json
from datetime import UTC, datetime
from pathlib import Path

import compare_engines
import pytest
from fakes import FakeModel

from meeting.settings import load
from meeting.summary import MeetingSummary
from meeting.transcript import Segment, Transcript

ROOT = Path(__file__).resolve().parents[2]
M01 = json.loads((ROOT / "eval" / "meetings" / "M01.json").read_text(encoding="utf-8"))
ANSWER = {
    "title": "Release planning",
    "overview": "The team planned the release.",
    "decisions": [{"text": "Release version two on the fifteenth of March.", "evidence": "00:30"}],
    "action_items": [{"task": "Send the analytics numbers.", "owner": "Omar", "due": "Wednesday", "evidence": "00:26"}],
    "open_questions": [],
}


def speech_transcript() -> Transcript:
    return Transcript(
        segments=[
            Segment(0.0, 6.0, "Good morning everyone. Omar, Leena, thanks for joining.", "Guest-1"),
            Segment(6.5, 9.0, "Morning. I have the test results.", "Guest-2"),
            Segment(9.5, 12.0, "Please go ahead.", "Guest-1"),
            Segment(26.0, 30.0, "Omar will send the analytics numbers by Wednesday.", "Guest-3"),
            Segment(30.0, 34.0, "We release version two on the fifteenth of March.", "Guest-1"),
        ],
        language="en-US",
        audio_seconds=84.2,
        seconds=95.0,
        engine="azure-speech batch 2025-10-15 uaenorth",
        warnings=["attendee names not passed: batch transcription takes no phrase list (D44)"],
    )


def test_split_blob():
    assert compare_engines.split_blob("transcripts/m7-m01-1/abc.azure-speech.json") == (
        "transcripts",
        "m7-m01-1/abc.azure-speech.json",
    )
    with pytest.raises(ValueError):
        compare_engines.split_blob("transcripts")


def test_speakers_in_order_of_first_appearance_and_none_from_whisper():
    assert compare_engines.speakers(speech_transcript()) == ["Guest-1", "Guest-2", "Guest-3"]
    whisper = Transcript([Segment(0.0, 1.0, "hello")], "en", 1.0, 1.0, "faster-whisper stt-small")
    assert compare_engines.speakers(whisper) == []


def test_names_heard_only_as_spelled_on_the_list():
    # "Leena" is how a transcriber without hints may spell Lina: it does not count as Lina heard (D44).
    assert compare_engines.names_heard(speech_transcript(), ["Sara", "Omar", "Lina"]) == ["Omar"]


def test_laptop_summary_scores_the_summary_against_the_answers():
    model = FakeModel(ANSWER)
    run = compare_engines.laptop_summary("laptop/speech", "speech", speech_transcript(), M01, None, model, load({}))
    assert model.calls == 1 and run.model == load({}).chat_model
    assert run.summary.action_items[0].owner == "Omar"
    labels = dict(run.checks)
    assert any(label.startswith("transcript WER") for label in labels)
    assert labels["decisions: 1 of 2 expected found (1 in the summary)"] is False  # dark mode missing
    assert run.seconds == 1.5 and run.completion_tokens == 120


def test_the_report_has_both_tables_and_carries_no_at_sign(monkeypatch, tmp_path):
    monkeypatch.setattr(compare_engines.Path, "home", lambda: tmp_path)
    summary = MeetingSummary.model_validate(ANSWER)
    speech = speech_transcript()
    whisper = Transcript(
        [Segment(0.0, 6.0, "Good morning everyone. Omar, Lina, thanks for joining.")],
        "en",
        84.2,
        29.8,
        f"faster-whisper {tmp_path}/models/stt-small",
    )
    runs = [
        compare_engines.Run("azure", "speech", "gpt-5.4-mini", summary, [("a check", True)], ["owner x removed"]),
        compare_engines.Run("laptop/whisper", "whisper", "gpt-5.4-mini", summary, [("a check", False)], [], 2.0, 9),
    ]
    report = compare_engines.render(
        M01, "m7-m01-1", {"speech": speech, "whisper": whisper}, runs, datetime(2026, 11, 25, tzinfo=UTC)
    )
    assert "@" not in report and str(tmp_path) not in report
    assert "| speech | azure-speech batch 2025-10-15 uaenorth | 5 |" in report
    assert "3 (script: 3) | 1 of 3: Omar |" in report  # three speaker labels, one name heard as spelled
    assert "none (script: 3) | 2 of 3: Omar, Lina |" in report
    assert "| azure | speech | gpt-5.4-mini | 1 | 1 | 0 | Omar | 1 of 1 | 1 | - | - |" in report
    assert "| laptop/whisper | whisper | gpt-5.4-mini | 1 | 1 | 0 | Omar | 0 of 1 | 0 | 2.0 | 9 |" in report
    assert "[00:00] Guest-1: Good morning everyone." in report
    assert "- grounding: owner x removed" in report


def test_azure_side_refuses_laptop_settings(monkeypatch):
    for name in ("RecordingsStorage__blobServiceUri", "COSMOS_ENDPOINT", "COSMOS_KEY"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(SystemExit, match=r"meet-azure\.env"):
        compare_engines.azure_side("m7-m01-1")


def test_passed_counts_checks_not_their_values():
    # The M7 summaries of M01: every kind found, one owner wrong -> 7 of 8, never "11 of 8" (D51).
    checks = [
        ("WER", True),
        ("decisions", True),
        ("actions", True),
        ("questions", True),
        ("owner", False),
        ("due", True),
        ("evidence", True),
        ("forbidden", True),
    ]
    assert compare_engines.passed(checks) == "7 of 8"
