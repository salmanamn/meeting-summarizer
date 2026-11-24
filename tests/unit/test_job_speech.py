"""The meeting job with Speech batch transcription (D44, D45): submitted once, waited for across deliveries, cleaned
up, and a recording Speech reads is still the one the job was received with."""

import pytest
from fakes import FakeRemoteTranscriber, wav_bytes
from test_job import ID, PATH, Lab

from meeting.job import transcript_blob_name
from meeting.speech import SpeechJobFailed, SpeechJobGone, SpeechUnavailable, TranscriptionPending


def speech_lab(outcomes=(), **settings) -> Lab:
    lab = Lab(stt_engine="speech", speech_endpoint="https://spch.example/", **settings)
    lab.stt = FakeRemoteTranscriber(outcomes=outcomes)
    return lab


def test_an_upload_is_submitted_by_url_and_becomes_a_summary():
    lab = speech_lab()
    lab.upload()
    assert lab.runner.handle(PATH).status == "summarised"
    assert lab.stt.submitted == [(f"https://strecfake.blob.core.windows.net/incoming/{ID}/recording.wav", ID, 2)]
    job = lab.job()
    assert (job["stage"], job["stt_runs"], job["speech"]["submissions"]) == ("summarised", 1, 1)
    sha = job["files"][0]["sha256"]
    assert job["transcript"]["blob"] == f"transcripts/{transcript_blob_name(ID, sha, 'azure-speech')}"
    assert lab.stt.deleted == lab.stt.waited[:1]  # the service's copy is deleted once ours is stored
    assert job["speech"]["job"] is None and job["speech"]["deleted_at"]


def test_a_speech_transcript_is_never_a_whisper_one():
    whisper, speech = Lab(), speech_lab()
    assert (whisper.settings.transcript_key, speech.settings.transcript_key) == ("stt-small", "azure-speech")


def test_a_job_still_running_is_polled_again_by_the_next_delivery_never_resubmitted():
    lab = speech_lab(outcomes=["pending", "pending"])
    lab.upload()
    for _ in range(2):
        with pytest.raises(TranscriptionPending):  # transient: the host delivers again at once
            lab.runner.handle(PATH)
        assert lab.job()["stage"] == "received" and lab.job()["speech"]["job"]
    assert lab.runner.handle(PATH).status == "summarised"
    assert len(lab.stt.submitted) == 1
    assert len(set(lab.stt.waited)) == 1 and len(lab.stt.waited) == 3  # one job, waited for three times
    assert lab.slept == []  # a running job is not an error to back off from


def test_waiting_runs_out_of_attempts_and_a_replay_still_polls_the_same_job():
    lab = speech_lab(outcomes=["pending", "pending"], job_max_attempts=2)
    lab.upload()
    with pytest.raises(TranscriptionPending):
        lab.runner.handle(PATH)
    outcome = lab.runner.handle(PATH)
    assert (outcome.status, outcome.detail) == ("failed", "retries_exhausted")  # recorded, not lost to a Conflict
    assert lab.job()["error"]["message"] == "TranscriptionPending on attempt 2 of 2"
    assert lab.runner.handle(PATH).status == "summarised"  # the replay (D18)
    assert len(lab.stt.submitted) == 1


def test_a_job_that_is_gone_is_submitted_again():
    lab = speech_lab(outcomes=["gone"])
    lab.upload()
    with pytest.raises(SpeechJobGone):
        lab.runner.handle(PATH)
    assert lab.job()["speech"]["job"] is None
    assert lab.runner.handle(PATH).status == "summarised"
    assert lab.job()["speech"]["submissions"] == 2


def test_a_service_failure_is_submitted_again_a_bad_recording_is_permanent():
    lab = speech_lab(outcomes=[SpeechJobFailed("InternalServerError", "x")])
    lab.upload()
    with pytest.raises(SpeechJobFailed):
        lab.runner.handle(PATH)
    assert lab.runner.handle(PATH).status == "summarised"
    assert len(lab.stt.submitted) == 2

    lab = speech_lab(outcomes=[SpeechJobFailed("InvalidAudioFormat", "not supported")])
    lab.upload()
    outcome = lab.runner.handle(PATH)
    assert (outcome.status, outcome.detail) == ("failed", "transcription_failed")
    assert lab.job()["error"]["retryable"] is False
    assert lab.runner.handle(PATH).status == "duplicate"  # the same manifest doesn't try again
    assert lab.llm.calls == 0


def test_speech_unavailable_waits_like_a_model_error():
    lab = speech_lab()
    lab.stt.submit_error = SpeechUnavailable("HTTP 503")
    lab.upload()
    with pytest.raises(SpeechUnavailable):
        lab.runner.handle(PATH)
    assert lab.slept == [30]
    assert lab.job()["speech"] is None  # nothing was submitted


def test_a_retry_hashes_the_blob_again_before_speech_reads_it():
    lab = speech_lab()
    lab.stt.submit_error = SpeechUnavailable("HTTP 503")
    lab.upload()
    with pytest.raises(SpeechUnavailable):
        lab.runner.handle(PATH)
    lab.blobs.put("incoming", f"{ID}/recording.wav", wav_bytes(3.0))  # replaced after it was received
    lab.stt.submit_error = None
    assert lab.runner.handle(PATH).detail == "hash_mismatch"
    assert lab.stt.submitted == []  # Speech never saw the other bytes


def test_the_first_attempt_submits_without_downloading_again():
    lab = speech_lab()
    lab.upload()
    lab.runner.handle(PATH)
    assert lab.blobs.downloads == [f"{ID}/recording.wav"]  # the check at the door only


def test_a_failed_cleanup_never_fails_the_job():
    lab = speech_lab()
    lab.stt.delete_error = SpeechUnavailable("HTTP 503")
    lab.upload()
    assert lab.runner.handle(PATH).status == "summarised"


def test_a_stored_speech_transcript_is_reused_without_a_new_job():
    lab = speech_lab()
    lab.upload()
    lab.llm.error = SpeechUnavailable("stands in for any error after the transcript is stored")
    with pytest.raises(SpeechUnavailable):
        lab.runner.handle(PATH)
    lab.llm.error = None
    assert lab.runner.handle(PATH).status == "summarised"
    assert len(lab.stt.submitted) == 1 and lab.job()["stt_runs"] == 1


def test_a_new_upload_after_a_failure_gets_a_new_speech_job():
    lab = speech_lab(outcomes=[SpeechJobFailed("InvalidAudioFormat", "x")])
    lab.upload()
    lab.runner.handle(PATH)
    lab.upload(audio=wav_bytes(3.0))  # a new manifest ETag restarts the failed job (D18)
    assert lab.runner.handle(PATH).status == "summarised"
    assert len(lab.stt.submitted) == 2


def test_a_delivery_that_loses_the_race_after_submitting_deletes_its_job():
    from meeting.stores import Conflict

    lab = speech_lab()
    lab.upload()
    replace = lab.jobs.replace

    def other_delivery_wrote_first(doc):
        if (doc.get("speech") or {}).get("job"):
            raise Conflict(doc["id"])
        return replace(doc)

    lab.jobs.replace = other_delivery_wrote_first
    assert lab.runner.handle(PATH).status == "duplicate"
    assert lab.stt.deleted == ["https://spch.example/speechtotext/transcriptions/1"]  # no orphan left running
