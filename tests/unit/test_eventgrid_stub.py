"""The local Event Grid stub (D12, D15): the events it builds, its filters, and its delivery rules, against a
webhook that answers the way the Functions blob extension does (HttpRequestProcessor in azure-sdk-for-net)."""

import json
import threading
import time
import urllib.parse
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import eventgrid_stub as stub
import pytest

CONFIG = json.loads((stub.ROOT / "emulators" / "eventgrid" / "subscriptions.json").read_text())
SUBSCRIPTION = CONFIG["subscriptions"][0]


def event(name: str = "m01-1/meeting.json", container: str = "incoming") -> dict:
    return stub.blob_created_event(
        account="devstoreaccount1",
        blob_endpoint="http://127.0.0.1:10000/devstoreaccount1",
        container=container,
        name=name,
        etag='"0x8DE1F2A3B4C5D6E"',
        size=412,
        content_type="application/json",
    )


def test_the_event_carries_what_the_blob_extension_reads():
    """The extension takes container and blob from data.url (BlobUriBuilder; an IP host means the account is the
    first path segment), the ETag from data.eTag (it adds the quotes) and the blob type from data.blobType."""
    e = event()
    assert e["eventType"] == "Microsoft.Storage.BlobCreated"
    assert e["subject"] == "/blobServices/default/containers/incoming/blobs/m01-1/meeting.json"
    url = urllib.parse.urlparse(e["data"]["url"])
    account, container, blob = url.path.lstrip("/").split("/", 2)
    assert (url.hostname, account, container, blob) == (
        "127.0.0.1",
        "devstoreaccount1",
        "incoming",
        "m01-1/meeting.json",
    )
    assert e["data"]["eTag"] == "0x8DE1F2A3B4C5D6E"
    assert e["data"]["blobType"].replace("Blob", "") == "Block"  # Enum.Parse(BlobType, ...) in the extension


def test_names_are_url_encoded():
    assert event("m01-1/agenda v2.pdf")["data"]["url"].endswith("/incoming/m01-1/agenda%20v2.pdf")


@pytest.mark.parametrize(
    ("name", "container", "delivered"),
    [
        ("m01-1/meeting.json", "incoming", True),
        ("m01-1/recording.wav", "incoming", False),  # the subject filter keeps recordings away from the function
        ("m01-1/meeting.json.bak", "incoming", False),
        ("m01-1/meeting.json", "transcripts", False),
    ],
)
def test_the_subscription_filter(name, container, delivered):
    assert stub.matches(SUBSCRIPTION, event(name, container)) is delivered
    assert not stub.matches(SUBSCRIPTION, {**event(), "eventType": "Microsoft.Storage.BlobDeleted"})


def test_changed_blobs():
    seen = {"incoming/a/meeting.json": '"1"', "incoming/a/r.wav": '"1"'}
    now = {"incoming/a/meeting.json": '"2"', "incoming/a/r.wav": '"1"', "incoming/b/meeting.json": '"1"'}
    assert stub.changed(seen, now) == ["incoming/a/meeting.json", "incoming/b/meeting.json"]
    assert stub.changed(now, now) == []


class BlobsWebhook:
    """Answers like /runtime/webhooks/blobs: handshake -> 200 + validationResponse; Notification -> the next status
    from `statuses` (the extension's own answer is 202); a request without aeg-event-type -> 400."""

    def __init__(self, statuses: list[int]) -> None:
        self.statuses = deque(statuses)
        self.notifications: list[dict] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                kind = self.headers.get("aeg-event-type")
                if kind == "SubscriptionValidation":
                    reply, status = {"validationResponse": body[0]["data"]["validationCode"]}, 200
                elif kind == "Notification":
                    owner.notifications.append({"count": self.headers.get("aeg-delivery-count"), "events": body})
                    reply, status = {}, owner.statuses.popleft() if owner.statuses else 202
                else:
                    reply, status = {}, 400
                data = json.dumps(reply).encode()
                self.send_response(status)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/runtime/webhooks/blobs?functionName=x"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def webhook(request):
    hook = BlobsWebhook(getattr(request, "param", []))
    yield hook
    hook.close()


def wait_for(record: deque, n: int = 1, timeout: float = 5.0) -> list[dict]:
    deadline = time.monotonic() + timeout
    while len(record) < n and time.monotonic() < deadline:
        time.sleep(0.02)
    return list(record)


def test_handshake_then_delivery(webhook, tmp_path, monkeypatch):
    monkeypatch.setattr(stub, "DATA", tmp_path)
    assert stub.validate(webhook.url, 5)
    record: deque = deque()
    sub = stub.Subscription({**SUBSCRIPTION, "endpoint": webhook.url}, [0], record).start()
    e = event()
    sub.events.put(e)
    (result,) = wait_for(record)
    assert sub.validated
    assert (result["result"], result["status"], result["attempts"]) == ("delivered", 202, 1)
    assert webhook.notifications == [{"count": "0", "events": [e]}]


@pytest.mark.parametrize("webhook", [[500, 503, 202]], indirect=True)
def test_retries_then_delivered(webhook, tmp_path, monkeypatch):
    monkeypatch.setattr(stub, "DATA", tmp_path)
    record: deque = deque()
    sub = stub.Subscription({**SUBSCRIPTION, "endpoint": webhook.url}, [0], record).start()
    sub.events.put(event())
    (result,) = wait_for(record)
    assert (result["result"], result["attempts"]) == ("delivered", 3)
    assert [n["count"] for n in webhook.notifications] == ["0", "1", "2"]


@pytest.mark.parametrize(("webhook", "attempts"), [([500] * 10, 3), ([400], 1)], indirect=["webhook"])
def test_dead_letter_after_the_last_attempt_or_at_once_on_400(webhook, attempts, tmp_path, monkeypatch):
    monkeypatch.setattr(stub, "DATA", tmp_path)
    record: deque = deque()
    sub = stub.Subscription({**SUBSCRIPTION, "endpoint": webhook.url, "maxDeliveryAttempts": 3}, [0], record).start()
    e = event()
    sub.events.put(e)
    (result,) = wait_for(record)
    assert (result["result"], result["attempts"]) == ("dead-lettered", attempts)
    letter = json.loads((tmp_path / "deadletter" / SUBSCRIPTION["name"] / f"{e['id']}.json").read_text())
    assert letter["event"] == e and letter["lastStatus"] == result["status"]


def test_no_header_is_a_bad_request_like_the_real_endpoint(webhook):
    status, _ = stub.post(webhook.url, [event()], "", 5)
    assert status == 400


def test_no_host_means_no_validation():
    assert stub.validate("http://127.0.0.1:9/runtime/webhooks/blobs", 1) is False
