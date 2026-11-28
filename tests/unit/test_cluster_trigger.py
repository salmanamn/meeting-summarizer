"""The app in a container on a cluster (Project 7): the queue trigger (D55), the Cosmos endpoint-discovery switch,
the stub's storage queue destination, and the models Job (D56). Flex keeps the Event Grid Blob trigger."""

import base64
import hashlib
import importlib
import importlib.util
import json
from collections import deque
from pathlib import Path

import azure.functions as func
import pytest

from meeting import fetch_job, stores
from meeting.events import EVENTS_QUEUE, manifest_name
from meeting.settings import SettingsInvalid, load, trigger

ROOT = Path(__file__).resolve().parents[2]
SUBJECT = "/blobServices/default/containers/incoming/blobs/m01-1/meeting.json"


def event(subject: str = SUBJECT, event_type: str = "Microsoft.Storage.BlobCreated") -> dict:
    return {"id": "e1", "eventType": event_type, "subject": subject, "data": {"url": "http://x/incoming/m01-1"}}


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (json.dumps(event()), "incoming/m01-1/meeting.json"),
        (json.dumps([event()]), "incoming/m01-1/meeting.json"),  # a batch of one, as a webhook gets it
        (json.dumps([event(), event()]), None),
        (json.dumps(event(event_type="Microsoft.Storage.BlobDeleted")), None),
        (json.dumps(event(SUBJECT.replace("/meeting.json", "/recording.wav"))), None),
        (json.dumps(event(SUBJECT.replace("/incoming/", "/transcripts/"))), None),
        ("not json", None),
        (json.dumps("a string"), None),
    ],
)
def test_manifest_name(body, expected):
    assert manifest_name(body, "incoming") == expected


def test_trigger_setting():
    assert trigger({}) == "eventgrid-blob" == load({}).trigger
    assert trigger({"MEETING_TRIGGER": "queue"}) == "queue"
    with pytest.raises(SettingsInvalid, match="MEETING_TRIGGER"):
        trigger({"MEETING_TRIGGER": "polling"})


@pytest.mark.parametrize(("value", "expected"), [(None, True), ("true", True), ("false", False), ("FALSE", False)])
def test_cosmos_endpoint_discovery(value, expected):
    env = {} if value is None else {"COSMOS_ENDPOINT_DISCOVERY": value}
    assert load(env).cosmos_endpoint_discovery is expected


def test_job_store_gets_the_discovery_switch(monkeypatch):
    seen = {}

    class FakeCosmosClient:
        def __init__(self, endpoint, credential, **kwargs):
            seen.update(kwargs, endpoint=endpoint)

        def get_database_client(self, name):
            return self

        def get_container_client(self, name):
            return self

    import azure.cosmos

    monkeypatch.setattr(azure.cosmos, "CosmosClient", FakeCosmosClient)
    settings = load(
        {"COSMOS_ENDPOINT": "http://192.168.58.114:8081", "COSMOS_KEY": "k", "COSMOS_ENDPOINT_DISCOVERY": "false"}
    )
    stores.JobStore.from_settings(settings)
    assert seen == {"endpoint": "http://192.168.58.114:8081", "enable_endpoint_discovery": False}


@pytest.fixture
def app_with(monkeypatch):
    import function_app

    def load_app(value: str | None):
        if value is None:
            monkeypatch.delenv("MEETING_TRIGGER", raising=False)
        else:
            monkeypatch.setenv("MEETING_TRIGGER", value)
        return importlib.reload(function_app)

    yield load_app
    monkeypatch.delenv("MEETING_TRIGGER", raising=False)
    importlib.reload(function_app)  # the other tests see the default app again


def bindings(module) -> dict[str, list[dict]]:
    return {f.get_function_name(): f.get_bindings_dict()["bindings"] for f in module.app.get_functions()}


def test_default_is_the_event_grid_blob_trigger(app_with):
    found = bindings(app_with(None))
    assert sorted(found) == ["health", "meeting_job", "meeting_status"]
    assert found["meeting_job"][0]["type"] == "blobTrigger"


def test_queue_trigger_replaces_the_blob_trigger(app_with):
    found = bindings(app_with("queue"))
    assert sorted(found) == ["health", "meeting_queue_job", "meeting_status"]
    (binding,) = found["meeting_queue_job"]
    assert binding["type"] == "queueTrigger"
    assert (binding["queueName"], binding["connection"]) == (EVENTS_QUEUE, "RecordingsStorage")


class Runner:
    def __init__(self):
        self.handled = []

    def handle(self, name):
        self.handled.append(name)
        from meeting.job import Outcome

        return Outcome("summarised", "m01-1", "test")


@pytest.mark.parametrize(("body", "handled"), [(event(), ["incoming/m01-1/meeting.json"]), (event(event_type="X"), [])])
def test_queue_job_hands_the_manifest_to_the_runner(app_with, monkeypatch, body, handled):
    module = app_with("queue")
    runner = Runner()
    monkeypatch.setattr(module, "_runner", lambda: runner)
    handler = module.meeting_queue_job.build().get_user_function()
    handler(func.QueueMessage(id="q1", body=json.dumps(body).encode()))
    assert runner.handled == handled


def test_queue_retries_agree_with_the_job():
    host = json.loads((ROOT / "src" / "host.json").read_text())
    queues = host["extensions"]["queues"]
    assert queues["maxDequeueCount"] == host["extensions"]["blobs"]["poisonBlobThreshold"] == load({}).job_max_attempts
    assert (queues["batchSize"], queues["newBatchThreshold"]) == (1, 0)  # one Whisper per instance
    assert queues["messageEncoding"] == "base64"  # what the stub writes, and Event Grid's queue handler


def load_stub():
    spec = importlib.util.spec_from_file_location("eventgrid_stub", ROOT / "scripts" / "eventgrid_stub.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stub_writes_queue_subscriptions_into_the_queue():
    stub = load_stub()
    config = json.loads((ROOT / "emulators" / "eventgrid" / "cluster.json").read_text())
    (sub,) = config["subscriptions"]
    assert stub.queue_destination(sub) == EVENTS_QUEUE and "endpoint" not in sub
    sent = []
    subscription = stub.Subscription(sub, [0.01], deque(), sender=lambda e: sent.append(e) or 201)
    assert subscription.validated  # no handshake for a queue
    one = stub.blob_created_event(
        account="devstoreaccount1",
        blob_endpoint="http://127.0.0.1:10000/devstoreaccount1",
        container="incoming",
        name="m01-1/meeting.json",
        etag='"0x1"',
        size=10,
        content_type="application/json",
    )
    assert stub.matches(sub, one)
    subscription._deliver(one)
    assert sent == [one] and subscription.record[-1]["result"] == "delivered"
    assert manifest_name(json.dumps(sent[0]), "incoming") == "incoming/m01-1/meeting.json"


def test_stub_queue_messages_are_base64_text(monkeypatch):
    from azure.storage.queue import TextBase64EncodePolicy

    stub = load_stub()
    sender = stub.QueueSender(EVENTS_QUEUE, "UseDevelopmentStorage=true")
    policy = sender.client._message_encode_policy
    assert isinstance(policy, TextBase64EncodePolicy)
    policy.configure(require_encryption=False, key_encryption_key=None, resolver=None)
    encoded = policy(json.dumps(event()))
    assert json.loads(base64.b64decode(encoded)) == event()


def test_stub_refuses_a_queue_destination_without_a_name():
    with pytest.raises(SystemExit, match="queueName"):
        load_stub().queue_destination({"name": "x", "destination": {"type": "storageQueue"}})


def test_laptop_stub_config_stays_a_webhook():
    config = json.loads((ROOT / "emulators" / "eventgrid" / "subscriptions.json").read_text())
    assert all("destination" not in s and s["endpoint"] for s in config["subscriptions"])


@pytest.fixture
def locked(tmp_path):
    data = b"whisper tiny config"
    lock = {
        "stt-tiny": {
            "repo": "Systran/faster-whisper-tiny",
            "revision": "abc123def456aaaa",
            "files": {"config.json": {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}},
        }
    }
    path = tmp_path / "models.lock.json"
    path.write_text(json.dumps(lock))
    return lock, path, data


def test_locked_hub_lists_and_addresses_only_locked_files(locked):
    lock, _, _ = locked
    hub = fetch_job.LockedHub(lock, "https://hf.example/")
    assert hub.list_files("Systran/faster-whisper-tiny", "abc123def456aaaa") == ["config.json"]
    url = hub.url("Systran/faster-whisper-tiny", "config.json", "abc123def456aaaa")
    assert url == "https://hf.example/Systran/faster-whisper-tiny/resolve/abc123def456aaaa/config.json"
    with pytest.raises(Exception, match="not locked"):
        hub.resolve_revision("Systran/faster-whisper-tiny")


def test_fetch_then_check(monkeypatch, tmp_path, locked, capsys):
    _, path, data = locked
    models = tmp_path / "models"
    monkeypatch.setenv("MODELS_LOCK", str(path))
    monkeypatch.setenv("MODELS_DIR", str(models))
    assert fetch_job.main(["check", "stt-tiny"]) == 1  # nothing there yet

    def download(self, repo, filename, revision, staging):
        target = staging / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target

    monkeypatch.setattr(fetch_job.LockedHub, "download", download)
    assert fetch_job.main(["fetch", "stt-tiny"]) == 0
    assert fetch_job.main(["check", "stt-tiny"]) == 0
    (models / "stt-tiny" / "config.json").write_bytes(b"tampered")
    assert fetch_job.main(["check", "stt-tiny"]) == 1
    assert "differs from the lock" in capsys.readouterr().out
    assert fetch_job.main(["check", "stt-small"]) == 1  # not in this lock
