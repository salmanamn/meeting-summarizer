"""The pipeline with a real transcriber (D36): Piper speaks M02, the upload contract puts it into Azurite (files
first, `meeting.json` last), Whisper tiny transcribes it, the stand-in model (scripts/fake_llm.py) answers over HTTP
through the real client, and the record lands in the Cosmos emulator. Only the model is a stand-in; no Functions host
(the trigger's binding is the local runs' job, M2).

Needs the lab up and two models on disk: uv run python scripts/fetch_models.py stt-tiny tts-en-libritts
"""

import dataclasses
import hashlib
import uuid
from pathlib import Path

import make_meeting
import openai
import pytest
import upload_meeting
from fake_llm import FakeLLM

from meeting.expect import wer
from meeting.job import JobRunner
from meeting.llm import JsonModel
from meeting.manifest import MANIFEST_NAME
from meeting.modelstore import read_lock, verify
from meeting.transcript import Transcript, stamp

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]
MODELS = ("stt-tiny", make_meeting.VOICE)
TINY_MAX_WER = 0.4  # Whisper tiny on clean synthetic speech; small stays under 0.15 (D7)


@pytest.fixture(scope="module")
def ci_settings(settings):
    return dataclasses.replace(settings, stt_model="stt-tiny", chat_model="fake", chat_reasoning_effort="none")


@pytest.fixture(scope="module")
def models(ci_settings):
    lock = read_lock(ROOT / "models.lock.json")
    problems = [p for name in MODELS for p in verify(name, ci_settings.models_dir, lock)]
    if problems:  # a failure, not a skip: CI must never pass without the transcriber it claims to test
        pytest.fail(f"{problems[0]} (run: uv run python scripts/fetch_models.py {' '.join(MODELS)})")
    return ci_settings.models_dir


@pytest.fixture(scope="module")
def recording(models, tmp_path_factory) -> Path:
    frames, rate = make_meeting.render(make_meeting.read_meeting("M02"), models, seed=0)
    path = tmp_path_factory.mktemp("m02") / "M02.wav"
    make_meeting.write_wav(path, frames, rate)
    return path


@pytest.fixture(scope="module")
def transcriber(ci_settings, models):
    from meeting.stt import WhisperTranscriber

    return WhisperTranscriber.from_settings(ci_settings)


@pytest.fixture(scope="module")
def fake():
    server = FakeLLM().start()
    yield server
    server.stop()


@pytest.fixture
def run(ci_settings, blobs, jobs, transcriber, fake):
    def model():
        return JsonModel(base_url=fake.url, api_key="ci", model="fake", reasoning_effort="none", timeout=30)

    runner = JobRunner(ci_settings, blobs, jobs, transcriber=lambda: transcriber, model=model, sleep=lambda s: None)
    return lambda meeting_id: runner.handle(f"{ci_settings.incoming_container}/{meeting_id}/{MANIFEST_NAME}")


def upload(blobs, settings, recording: Path, *, sha256: str | None = None) -> str:
    """The upload contract (D15), with the uploader's own manifest builder: the recording, then meeting.json."""
    meeting_id = f"ci-{uuid.uuid4().hex[:8]}"
    manifest = upload_meeting.build_manifest(meeting_id, "Weekly status", ["Lina", "Omar"], recording, [])
    if sha256:
        manifest = manifest.model_copy(update={"recording": manifest.recording.model_copy(update={"sha256": sha256})})
    container = blobs.service.get_container_client(settings.incoming_container)
    container.upload_blob(f"{meeting_id}/{recording.name}", recording.read_bytes())
    container.upload_blob(f"{meeting_id}/{MANIFEST_NAME}", manifest.model_dump_json().encode())
    return meeting_id


def stored_transcript(blobs, job) -> Transcript:
    container, _, name = job["transcript"]["blob"].partition("/")
    return Transcript.from_json(blobs.read_text(container, name))


def test_a_spoken_meeting_becomes_a_grounded_summary(run, blobs, jobs, ci_settings, recording, fake):
    meeting_id = upload(blobs, ci_settings, recording)
    before = len(fake.requests)
    outcome = run(meeting_id)
    assert (outcome.status, outcome.detail) == ("summarised", "attempt 1")
    job = jobs.get(meeting_id)
    assert (job["stage"], job["stt_runs"], job["attempts"]) == ("summarised", 1, 1)
    transcript = stored_transcript(blobs, job)
    assert transcript.engine == "faster-whisper stt-tiny batched" and transcript.segments
    assert 15 < transcript.audio_seconds < 30  # M02 is about 21 s
    script = " ".join(text for _, text in make_meeting.read_meeting("M02")["lines"])
    assert wer(script, transcript.text) <= TINY_MAX_WER, transcript.text  # it heard the meeting (M3 measures how well)
    # One call, with the transcript's own times as the only evidence on offer (D14)...
    assert len(fake.requests) == before + 1
    schema = fake.requests[-1]["response_format"]["json_schema"]["schema"]
    offered = schema["properties"]["decisions"]["items"]["properties"]["evidence"]["anyOf"][0]["enum"]
    assert offered == [stamp(s.start) for s in transcript.segments]
    # ... and the stand-in's decision survives grounding unchanged: a line of the transcript at its own time.
    [decision] = job["summary"]["decisions"]
    line = next(s for s in transcript.segments if s.text == decision["text"])
    assert decision["evidence"] == stamp(line.start)
    assert job["summary_meta"]["grounding_warnings"] == []


def test_a_second_delivery_redoes_nothing(run, blobs, jobs, ci_settings, recording, fake):
    meeting_id = upload(blobs, ci_settings, recording)
    assert run(meeting_id).status == "summarised"
    calls = len(fake.requests)
    assert run(meeting_id).status == "duplicate"
    job = jobs.get(meeting_id)
    assert (job["deliveries"], job["stt_runs"], len(fake.requests)) == (2, 1, calls)


def test_a_model_error_is_retried_without_transcribing_again(run, blobs, jobs, ci_settings, recording, fake):
    meeting_id = upload(blobs, ci_settings, recording)
    fake.next_status = [503]
    with pytest.raises(openai.InternalServerError):  # the host would retry the delivery
        run(meeting_id)
    job = jobs.get(meeting_id)
    assert (job["stage"], job["attempts"], job["stt_runs"]) == ("transcribed", 1, 1)
    assert run(meeting_id).status == "summarised"
    job = jobs.get(meeting_id)
    assert (job["stage"], job["attempts"], job["stt_runs"]) == ("summarised", 2, 1)  # the stored transcript reused


def test_a_recording_that_differs_from_its_manifest_never_reaches_a_model(
    run, blobs, jobs, ci_settings, recording, fake
):
    calls = len(fake.requests)
    meeting_id = upload(blobs, ci_settings, recording, sha256=hashlib.sha256(b"something else").hexdigest())
    outcome = run(meeting_id)
    assert (outcome.status, outcome.detail) == ("failed", "hash_mismatch")
    job = jobs.get(meeting_id)
    assert (job["stage"], job["error"]["stage"], job["transcript"]) == ("failed", "received", None)
    assert len(fake.requests) == calls
