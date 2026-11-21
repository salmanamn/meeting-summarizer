"""meeting.stores against Azurite and the Cosmos DB emulator, and one job through both with fake models."""

import hashlib
import json
import uuid

import pytest
from fakes import FakeModel, FakeTranscriber, wav_bytes

from meeting.job import JobRunner
from meeting.stores import Conflict, TooLarge

pytestmark = pytest.mark.integration


def test_blob_read_returns_content_and_etag_together(blobs, settings):
    c = settings.incoming_container
    blobs.service.get_blob_client(c, "a/meeting.json").upload_blob(b'{"x": 1}')
    data, etag = blobs.read(c, "a/meeting.json", 1024)
    assert data == b'{"x": 1}' and etag == blobs.info(c, "a/meeting.json").etag
    with pytest.raises(TooLarge):
        blobs.read(c, "a/meeting.json", 3)
    assert blobs.read(c, "a/none.json", 1024) is None and blobs.info(c, "a/none.json") is None


def test_blob_head_hash_and_text(blobs, settings, tmp_path):
    c, data = settings.incoming_container, wav_bytes(1.0)
    blobs.service.get_blob_client(c, "b/r.wav").upload_blob(data)
    assert blobs.head(c, "b/r.wav", 12) == data[:12]
    target = tmp_path / "r.wav"
    assert blobs.sha256(c, "b/r.wav", len(data), target) == hashlib.sha256(data).hexdigest()
    assert target.read_bytes() == data
    with pytest.raises(TooLarge):
        blobs.sha256(c, "b/r.wav", len(data) - 1)
    blobs.write_text(settings.transcripts_container, "b/t.json", "héllo")
    assert blobs.read_text(settings.transcripts_container, "b/t.json") == "héllo"


def test_job_records_are_compare_and_swap(jobs):
    job_id = f"j-{uuid.uuid4().hex[:8]}"
    first = jobs.create({"id": job_id, "stage": "received", "deliveries": 1})
    with pytest.raises(Conflict):
        jobs.create({"id": job_id})
    second = jobs.replace({**first, "stage": "transcribed"})
    with pytest.raises(Conflict):
        jobs.replace({**first, "stage": "summarised"})  # stale ETag: another delivery wrote in between
    jobs.increment(job_id, "deliveries")
    got = jobs.get(job_id)
    assert (got["stage"], got["deliveries"]) == ("transcribed", 2) and got["_etag"] != second["_etag"]
    assert jobs.get("j-none") is None


def test_a_job_through_the_real_stores(blobs, jobs, settings):
    meeting_id, recording = f"m-{uuid.uuid4().hex[:8]}", wav_bytes(2.0)
    c = settings.incoming_container
    blobs.service.get_blob_client(c, f"{meeting_id}/recording.wav").upload_blob(recording)
    manifest = {
        "schema_version": 1,
        "meeting_id": meeting_id,
        "title": "Integration",
        "language": "en",
        "attendees": ["Omar"],
        "recording": {"name": "recording.wav", "size": len(recording), "sha256": hashlib.sha256(recording).hexdigest()},
        "attachments": [],
    }
    blobs.service.get_blob_client(c, f"{meeting_id}/meeting.json").upload_blob(json.dumps(manifest))
    answer = {"title": "t", "overview": "o", "decisions": [], "action_items": [], "open_questions": []}
    runner = JobRunner(settings, blobs, jobs, FakeTranscriber, lambda: FakeModel(answer))
    path = f"{c}/{meeting_id}/meeting.json"
    assert runner.handle(path).status == "summarised"
    assert runner.handle(path).status == "duplicate"
    job = jobs.get(meeting_id)
    assert (job["stage"], job["attempts"], job["deliveries"]) == ("summarised", 1, 2)
    assert blobs.read_text(*job["transcript"]["blob"].split("/", 1))
