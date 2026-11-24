"""The pipeline with the Speech transcriber (D44, D45): the real client over HTTP against scripts/fake_speech.py, the
upload in Azurite, the record in the Cosmos emulator, the stand-in model over HTTP. What it proves: the job hands
Speech the recording's plain blob URL, keeps the Speech job on the record, waits for it across deliveries without
submitting twice, deletes it afterwards, and never sends its token anywhere but the Speech endpoint.

The fake answers with the documented result in tests/fixtures/speech/ whatever the audio is: transcription quality is
M7's comparison with Whisper on Azure, not this test's.
"""

import dataclasses
import uuid
from pathlib import Path

import pytest
import upload_meeting
from fake_llm import FakeLLM
from fake_speech import FakeSpeech
from fakes import wav_bytes

from meeting.job import JobRunner
from meeting.llm import JsonModel
from meeting.manifest import MANIFEST_NAME
from meeting.speech import SpeechTranscriber, TranscriptionPending
from meeting.transcript import Transcript, stamp

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def speech_settings(settings):
    return dataclasses.replace(
        settings,
        stt_engine="speech",
        speech_endpoint="http://127.0.0.1/",
        chat_model="fake",
        chat_reasoning_effort="none",
    )


@pytest.fixture(scope="module")
def llm():
    server = FakeLLM().start()
    yield server
    server.stop()


@pytest.fixture
def speech():
    server = FakeSpeech().start()
    yield server
    server.stop()


@pytest.fixture
def recording(tmp_path) -> Path:
    path = tmp_path / "recording.wav"
    path.write_bytes(wav_bytes(21.4))  # the length of the fixture's meeting; the fake doesn't listen to it
    return path


@pytest.fixture
def run(speech_settings, blobs, jobs, llm, speech):
    transcriber = SpeechTranscriber(
        speech.url, token=lambda: "ci-token", region="ci", poll_seconds=1, wait_seconds=1, sleep=lambda s: None
    )

    def model():
        return JsonModel(base_url=llm.url, api_key="ci", model="fake", reasoning_effort="none", timeout=30)

    runner = JobRunner(speech_settings, blobs, jobs, transcriber=lambda: transcriber, model=model, sleep=lambda s: None)
    return lambda meeting_id: runner.handle(f"{speech_settings.incoming_container}/{meeting_id}/{MANIFEST_NAME}")


def upload(blobs, settings, recording: Path) -> str:
    meeting_id = f"ci-speech-{uuid.uuid4().hex[:8]}"
    manifest = upload_meeting.build_manifest(meeting_id, "Weekly status", ["Sara", "Omar"], recording, [])
    container = blobs.service.get_container_client(settings.incoming_container)
    container.upload_blob(f"{meeting_id}/{recording.name}", recording.read_bytes())
    container.upload_blob(f"{meeting_id}/{MANIFEST_NAME}", manifest.model_dump_json().encode())
    return meeting_id


def stored_transcript(blobs, job) -> Transcript:
    container, _, name = job["transcript"]["blob"].partition("/")
    return Transcript.from_json(blobs.read_text(container, name))


def test_an_upload_is_transcribed_by_speech_and_summarised(run, blobs, jobs, speech_settings, recording, speech, llm):
    meeting_id = upload(blobs, speech_settings, recording)
    assert run(meeting_id).status == "summarised"
    (body,) = speech.submitted
    blob_url = blobs.url(speech_settings.incoming_container, f"{meeting_id}/recording.wav")
    assert body["contentUrls"] == [blob_url] and "?" not in blob_url  # the plain URL, no SAS (D3)
    job = jobs.get(meeting_id)
    assert (job["stage"], job["stt_runs"], job["speech"]["submissions"], job["speech"]["job"]) == (
        "summarised",
        1,
        1,
        None,
    )
    transcript = stored_transcript(blobs, job)
    assert transcript.engine == "azure-speech batch 2025-10-15 ci" and len(transcript.segments) == 4
    assert job["transcript"]["blob"].endswith(".azure-speech.json")
    # The summary saw the speakers' labels and cited a Speech phrase at its own time (the stand-in's longest line).
    [decision] = job["summary"]["decisions"]
    line = next(s for s in transcript.segments if s.text == decision["text"])
    assert decision["evidence"] == stamp(line.start) and line.speaker == "Guest-1"
    assert "Guest-1: " in llm.requests[-1]["messages"][1]["content"]
    # Cleaned up, and the token went to the Speech API only.
    assert [j["deleted"] for j in speech.jobs.values()] == [True]
    assert all(token for _, path, token in speech.requests if path.startswith("/speechtotext/"))
    assert not any(token for _, path, token in speech.requests if path.startswith("/_content/"))


def test_a_long_job_is_waited_for_by_later_deliveries(run, blobs, jobs, speech_settings, recording, speech):
    speech.running_polls = 2  # each delivery polls once (wait_seconds=1), so the third one finds it done
    meeting_id = upload(blobs, speech_settings, recording)
    for attempt in (1, 2):
        with pytest.raises(TranscriptionPending):
            run(meeting_id)
        job = jobs.get(meeting_id)
        assert (job["stage"], job["attempts"], job["speech"]["submissions"]) == ("received", attempt, 1)
    assert run(meeting_id).status == "summarised"
    assert len(speech.submitted) == 1
    assert jobs.get(meeting_id)["attempts"] == 3


def test_a_recording_speech_can_t_read_fails_for_good(run, blobs, jobs, speech_settings, recording, speech, llm):
    speech.outcome = "failed-audio"
    calls = len(llm.requests)
    meeting_id = upload(blobs, speech_settings, recording)
    outcome = run(meeting_id)
    assert (outcome.status, outcome.detail) == ("failed", "transcription_failed")
    job = jobs.get(meeting_id)
    assert (job["error"]["retryable"], job["error"]["message"]) == (
        False,
        "InvalidAudioFormat: The format of input audio is not supported.",
    )
    assert len(llm.requests) == calls
