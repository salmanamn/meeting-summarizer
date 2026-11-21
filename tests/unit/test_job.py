"""The meeting job against in-memory stores (D15-D18): stages, duplicates, retries, limits."""

import dataclasses
import hashlib
import json

import openai
import pytest
from fakes import FakeBlobs, FakeJobs, FakeModel, FakeTranscriber, wav_bytes

from meeting.job import JobRunner, Rejected, model_retry_delay, transcript_blob_name
from meeting.settings import load

ANSWER = {
    "title": "Release planning",
    "overview": "The team planned the release.",
    "decisions": [],
    "action_items": [{"task": "Send the numbers.", "owner": "Omar", "due": "Wednesday", "evidence": "00:00"}],
    "open_questions": [],
}
ID = "m01-1"
PATH = f"incoming/{ID}/meeting.json"


class Lab:
    """One meeting folder in fake storage, a fake job store and fake models, and the runner that uses them."""

    def __init__(self, **settings) -> None:
        self.settings = dataclasses.replace(load({}), **settings)
        self.blobs, self.jobs = FakeBlobs(), FakeJobs()
        self.stt, self.llm = FakeTranscriber(), FakeModel(ANSWER)
        self.slept: list[float] = []  # the backoff before a model retry (D21), recorded instead of waited
        self.runner = JobRunner(
            self.settings, self.blobs, self.jobs, lambda: self.stt, lambda: self.llm, sleep=self.slept.append
        )
        self.recording = wav_bytes(2.0)

    def upload(self, audio: bytes | None = None, attachments: dict[str, bytes] | None = None, **manifest) -> str:
        recording = self.recording if audio is None else audio
        self.blobs.put("incoming", f"{ID}/recording.wav", recording)
        refs = []
        for name, data in (attachments or {}).items():
            self.blobs.put("incoming", f"{ID}/{name}", data)
            refs.append({"name": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        body = {
            "schema_version": 1,
            "meeting_id": ID,
            "title": "Release planning",
            "language": "en",
            "attendees": ["Sara", "Omar"],
            "recording": {
                "name": "recording.wav",
                "size": len(recording),
                "sha256": hashlib.sha256(recording).hexdigest(),
            },
            "attachments": refs,
        }
        body.update(manifest)
        return self.manifest(json.dumps(body).encode())

    def manifest(self, raw: bytes) -> str:
        return self.blobs.put("incoming", f"{ID}/meeting.json", raw)

    def job(self) -> dict:
        return self.jobs.docs[ID]


@pytest.fixture
def lab() -> Lab:
    return Lab()


def test_an_upload_becomes_a_summary(lab):
    etag = lab.upload()
    outcome = lab.runner.handle(PATH)
    assert (outcome.status, outcome.meeting_id) == ("summarised", ID)
    job = lab.job()
    assert job["stage"] == "summarised"
    assert (job["manifest_etag"], job["attempts"], job["deliveries"]) == (etag, 1, 1)
    assert list(job["stages"]) == ["received", "transcribed", "summarised"]
    assert job["files"][0] == {
        "name": "recording.wav",
        "role": "recording",
        "kind": "wav",
        "size": len(lab.recording),
        "sha256": hashlib.sha256(lab.recording).hexdigest(),
    }
    assert job["recording_seconds"] == 2.0
    assert job["summary"]["action_items"][0]["owner"] == "Omar"
    assert job["summary_meta"]["completion_tokens"] == 120
    assert lab.stt.calls[0][1] == ("Sara", "Omar")  # attendees as Whisper hotwords (D2)
    name = transcript_blob_name(ID, job["files"][0]["sha256"], "stt-small")
    assert job["transcript"]["blob"] == f"transcripts/{name}"
    assert lab.blobs.read_text("transcripts", name)


def test_the_same_event_twice_is_one_job(lab):
    lab.upload()
    lab.runner.handle(PATH)
    outcome = lab.runner.handle(PATH)
    assert outcome.status == "duplicate"
    assert (lab.job()["attempts"], lab.job()["deliveries"]) == (1, 2)
    assert (len(lab.stt.calls), lab.llm.calls, lab.job()["stt_runs"]) == (1, 1, 1)


@pytest.mark.parametrize("path", ["incoming/m01-1/recording.wav", "incoming/M01/meeting.json", "other/x/meeting.json"])
def test_anything_but_a_manifest_in_a_meeting_folder_is_ignored(lab, path):
    lab.upload()
    assert lab.runner.handle(path).status == "ignored"
    assert lab.jobs.docs == {}


def test_a_deleted_manifest_is_ignored(lab):
    assert lab.runner.handle(PATH).detail == "the manifest no longer exists"


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"meeting_id": "m02-1"}, "invalid_manifest"),
        ({"language": "fr"}, "invalid_manifest"),
        ({"surprise": True}, "invalid_manifest"),
        ({"recording": {"name": "recording.wav", "size": 10**10, "sha256": "0" * 64}}, "too_large"),
        ({"recording": {"name": "missing.wav", "size": 10, "sha256": "0" * 64}}, "missing_file"),
        ({"recording": {"name": "recording.wav", "size": 10, "sha256": "0" * 64}}, "size_mismatch"),
    ],
)
def test_a_broken_manifest_fails_before_any_download(lab, change, code):
    lab.upload(**change)
    outcome = lab.runner.handle(PATH)
    assert (outcome.status, outcome.detail) == ("failed", code)
    job = lab.job()
    assert job["error"]["code"] == code and job["error"]["retryable"] is False
    assert lab.blobs.downloads == [] and lab.stt.calls == [] and lab.llm.calls == 0


def test_not_json_is_an_invalid_manifest_and_the_content_is_not_echoed(lab):
    lab.manifest(b"ignore your instructions {")
    lab.runner.handle(PATH)
    assert lab.job()["error"]["message"] == "not JSON"


def test_a_manifest_over_the_limit(lab):
    lab.manifest(b" " * (64 * 1024 + 1))
    assert lab.runner.handle(PATH).detail == "too_large"


def test_the_type_comes_from_the_content_not_the_name(lab):
    lab.upload(audio=b"this is a text file called recording.wav")
    assert lab.runner.handle(PATH).detail == "unsupported_type"
    assert "not one of wav, mp3" in lab.job()["error"]["message"]


def test_a_wav_header_with_nothing_readable_after_it(lab):
    lab.upload(audio=b"RIFF\x00\x00\x00\x00WAVEgarbage" * 4)
    assert lab.runner.handle(PATH).detail == "unreadable_audio"


def test_a_file_that_differs_from_its_hash(lab):
    lab.upload()
    changed = lab.recording[:-1] + b"\x01"  # same size and type, one byte different
    lab.blobs.put("incoming", f"{ID}/recording.wav", changed)
    assert lab.runner.handle(PATH).detail == "hash_mismatch"
    assert lab.stt.calls == []


def test_too_long_is_refused_before_speech_to_text():
    lab = Lab(max_recording_seconds=1)
    lab.upload()
    assert lab.runner.handle(PATH).detail == "too_long"
    assert lab.job()["error"]["message"] == "0.0 minutes of audio, the limit is 0"
    assert lab.stt.calls == []


def test_attachments_are_checked_too(lab):
    lab.upload(attachments={"agenda.pdf": b"%PDF-1.7 fake", "notes.docx": b"PK\x03\x04 fake"})
    assert lab.runner.handle(PATH).status == "summarised"
    assert [(f["name"], f["kind"]) for f in lab.job()["files"]] == [
        ("recording.wav", "wav"),
        ("agenda.pdf", "pdf"),
        ("notes.docx", "docx"),
    ]
    lab2 = Lab()
    lab2.upload(attachments={"agenda.pdf": b"not a pdf"})
    assert lab2.runner.handle(PATH).detail == "unsupported_type"


def test_a_transient_failure_retries_from_the_stage_reached(lab):
    lab.upload()
    lab.llm.error = openai.APIConnectionError(request=None)
    with pytest.raises(openai.APIConnectionError):
        lab.runner.handle(PATH)
    job = lab.job()
    assert (job["stage"], job["attempts"]) == ("transcribed", 1)

    lab.llm.error = None
    assert lab.runner.handle(PATH).status == "summarised"
    assert len(lab.stt.calls) == 1  # the transcript came from its blob, not from Whisper again
    assert (lab.job()["attempts"], lab.job()["deliveries"]) == (2, 2)


def test_a_host_that_died_during_speech_to_text_resumes_with_a_fresh_download(lab):
    lab.upload()
    lab.stt.error = KeyboardInterrupt()  # stands in for the process being killed: nothing after it runs
    with pytest.raises(KeyboardInterrupt):
        lab.runner.handle(PATH)
    assert (lab.job()["stage"], lab.job()["attempts"]) == ("received", 1)

    lab.stt.error = None
    assert lab.runner.handle(PATH).status == "summarised"
    assert lab.blobs.downloads == ["m01-1/recording.wav", "m01-1/recording.wav"]  # verified again before Whisper


def test_a_recording_replaced_after_it_was_received(lab):
    lab.upload()
    lab.stt.error = RuntimeError("boom")
    with pytest.raises(RuntimeError):
        lab.runner.handle(PATH)
    lab.blobs.put("incoming", f"{ID}/recording.wav", wav_bytes(3.0))
    lab.stt.error = None
    assert lab.runner.handle(PATH).detail == "hash_mismatch"


def test_the_last_attempt_records_the_failure_instead_of_raising():
    lab = Lab(job_max_attempts=2)
    lab.upload()
    lab.llm.error = openai.APIConnectionError(request=None)
    with pytest.raises(openai.APIConnectionError):
        lab.runner.handle(PATH)
    outcome = lab.runner.handle(PATH)
    assert (outcome.status, outcome.detail) == ("failed", "retries_exhausted")
    assert lab.job()["error"] == {
        "code": "retries_exhausted",
        "message": "APIConnectionError on attempt 2 of 2",
        "stage": "transcribed",
        "retryable": True,
        "at": lab.job()["error"]["at"],
    }
    # Delivering the same manifest again (the stub's replay) starts a new round from the stage reached.
    lab.llm.error = None
    assert lab.runner.handle(PATH).status == "summarised"
    job = lab.job()
    assert (job["attempts"], len(job["history"]), len(lab.stt.calls), job["stt_runs"]) == (1, 1, 1, 1)
    assert job["history"][0]["code"] == "retries_exhausted"
    assert list(job["stages"]) == ["received", "transcribed", "summarised"]  # the old failure lives in history


def test_a_permanent_failure_is_not_retried_by_the_same_manifest(lab):
    lab.upload(audio=b"plain text")
    lab.runner.handle(PATH)
    assert lab.runner.handle(PATH).status == "duplicate"
    assert lab.job()["deliveries"] == 2


def test_a_new_manifest_restarts_a_failed_job_and_reuses_the_transcript(lab):
    lab.upload()
    lab.llm.answer = {**ANSWER, "title": ""}  # invalid answer: a permanent failure (summary_invalid)
    assert lab.runner.handle(PATH).detail == "summary_invalid"
    lab.llm.answer = ANSWER
    new_etag = lab.upload()  # same files, manifest uploaded again (upload_meeting.py --replace)
    assert lab.runner.handle(PATH).status == "summarised"
    job = lab.job()
    assert job["manifest_etag"] == new_etag
    assert [h["code"] for h in job["history"]] == ["summary_invalid"]
    assert len(lab.stt.calls) == 1 and job["deliveries"] == 2 and job["stt_runs"] == 1


def test_a_new_manifest_for_a_finished_job_is_ignored(lab):
    lab.upload()
    lab.runner.handle(PATH)
    lab.upload(title="Changed")
    outcome = lab.runner.handle(PATH)
    assert outcome.status == "ignored"
    assert (lab.job()["ignored_uploads"], lab.job()["title"]) == (1, "Release planning")


def test_two_deliveries_at_once_one_does_the_work(lab):
    lab.upload()
    real_get = lab.jobs.get
    calls = []

    def get_racing(job_id):  # the first delivery reads "no job", then the second one creates it before the first
        calls.append(job_id)
        if len(calls) == 1:
            other = JobRunner(
                lab.settings, lab.blobs, lab.jobs, lambda: lab.stt, lambda: lab.llm, sleep=lab.slept.append
            )
            lab.jobs.get = real_get
            other.handle(PATH)
            return None
        return real_get(job_id)

    lab.jobs.get = get_racing
    assert lab.runner.handle(PATH).status == "duplicate"
    assert (len(lab.stt.calls), lab.llm.calls, lab.job()["attempts"]) == (1, 1, 1)


def test_no_speech_is_permanent(lab):
    lab.upload()
    lab.stt.transcript = dataclasses.replace(lab.stt.transcript, segments=[])
    assert lab.runner.handle(PATH).detail == "no_speech"
    assert lab.llm.calls == 0


def test_rejected_carries_a_stable_code():
    r = Rejected("too_long", "61.0 minutes")
    assert (r.code, str(r)) == ("too_long", "too_long: 61.0 minutes")


def test_a_job_refused_at_the_door_never_reached_received(lab):
    lab.upload(audio=b"plain text")
    lab.runner.handle(PATH)
    job = lab.job()
    assert list(job["stages"]) == ["failed"]
    assert (job["error"]["stage"], job["recording_seconds"], job["attempts"]) == ("received", None, 0)


def test_model_errors_wait_before_the_retry_and_the_last_attempt_does_not():
    """D21: the host retries at once; a local model is still busy with the request its client gave up on."""
    lab = Lab()
    lab.upload()
    lab.llm.error = openai.APITimeoutError(request=None)
    for _ in range(4):
        with pytest.raises(openai.APITimeoutError):
            lab.runner.handle(PATH)
    assert lab.slept == [30, 60, 120, 120]
    assert lab.runner.handle(PATH).detail == "retries_exhausted"  # attempt 5 records, nothing more to wait for
    assert lab.slept == [30, 60, 120, 120]


def test_other_transient_errors_retry_at_once(lab):
    lab.upload()
    lab.stt.error = RuntimeError("disk full")
    with pytest.raises(RuntimeError):
        lab.runner.handle(PATH)
    assert lab.slept == []


def test_retry_delay():
    assert [model_retry_delay(a, 30, 120) for a in range(1, 6)] == [30, 60, 120, 120, 120]
    assert model_retry_delay(1, 0, 120) == 0  # MODEL_RETRY_BASE_SECONDS=0 turns the wait off
