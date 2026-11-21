"""The helper scripts' own logic: the manifest the uploader builds, and what the status script prints."""

import json

import meeting_status
import upload_meeting
from fakes import wav_bytes

from meeting.manifest import parse


def test_the_uploader_builds_a_manifest_the_job_accepts(tmp_path):
    recording = tmp_path / "M01.wav"
    recording.write_bytes(wav_bytes(1.0))
    agenda = tmp_path / "agenda.pdf"
    agenda.write_bytes(b"%PDF-1.7")
    manifest = upload_meeting.build_manifest("m01-1", "Planning", ["Sara", "Omar"], recording, [agenda])
    again = parse(manifest.model_dump_json().encode(), "m01-1")
    assert again == manifest
    assert [f.name for f in again.files] == ["M01.wav", "agenda.pdf"]
    assert again.recording.size == recording.stat().st_size


def test_evidence_is_masked(monkeypatch, tmp_path):
    monkeypatch.setattr(meeting_status.Path, "home", lambda: tmp_path)
    assert meeting_status.mask(f"{tmp_path}/x user@example.com") == "~/x user at example.com"


def test_stage_lines():
    job = {
        "files": [{}],
        "stt_runs": 1,
        "recording_seconds": 83.8,
        "transcript": {"segments": 39, "audio_seconds": 83.8, "seconds": 30.2, "engine": "faster-whisper stt-small"},
        "summary_meta": {"model": "phi4-mini:3.8b", "seconds": 49.9, "completion_tokens": 417},
        "error": {"code": "too_long", "stage": "received", "message": "61.0 minutes", "retryable": False},
    }
    assert meeting_status.stage_line(job, "received") == "1 file(s), 83.8 s of audio"
    assert meeting_status.stage_line(job, "transcribed").endswith("(faster-whisper stt-small; Whisper runs so far: 1)")
    assert meeting_status.stage_line(job, "summarised") == "phi4-mini:3.8b, 49.9 s, 417 completion tokens"
    assert meeting_status.stage_line(job, "failed") == "too_long at received: 61.0 minutes"
    assert json.dumps(job)
