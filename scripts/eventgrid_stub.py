"""Local Event Grid stub for Blob storage events (D12, D15): watches Azurite and pushes BlobCreated events to the
Functions host's blobs webhook, the way an Event Grid system topic on the storage account does on Azure.

uv run python scripts/eventgrid_stub.py [--config emulators/eventgrid/subscriptions.json] [--port 6100] [--reset]

What it does, and what Event Grid does the same way:
- Watches the configured containers (Azurite has no change feed, so it lists them every `pollSeconds`). A new blob,
  or a blob whose ETag changed, is one `Microsoft.Storage.BlobCreated` event in the Event Grid schema, with the
  `data.url`, `data.eTag` and `data.blobType` the Functions blob extension reads.
- Filters per subscription: event type, `subjectBeginsWith`, `subjectEndsWith` (`/meeting.json` here, so recordings
  and attachments never reach the function).
- Before the first delivery, the subscription validation handshake (`aeg-event-type: SubscriptionValidation`); the
  blob extension answers with the validation code. Until it does (host not started yet), events wait.
- Delivery: `aeg-event-type: Notification`, 200-204 = delivered, retries after 2/4/8/16 s up to
  `maxDeliveryAttempts`, 400/413 dead-letter at once, otherwise dead-letter after the last attempt: one JSON file
  per event in data/eventgrid/deadletter/<subscription>/.
- At-least-once: `POST /_stub/replay {"subject_endswith": "<id>/meeting.json"}` sends the last such event again
  with the same id, which is what an Event Grid duplicate looks like.
- A subscription with `"destination": {"type": "storageQueue", "queueName": ...}` instead of `endpoint` writes each
  event into that queue (QUEUE_CONN, default BLOB_CONN), base64-encoded like the Functions queue trigger expects:
  Event Grid's storage queue handler (Project 7, D55). No handshake; a failed write is retried like a webhook.
Not emulated: other event types (BlobDeleted, ...), batching, CloudEvents schema, delivery identity, the webhook key
(`code=`; the local host doesn't ask for it).

State: the ETags already seen are kept in data/eventgrid/state.json, so a restart sends nothing for old blobs. The
first start (or --reset) records what exists without sending events: a new subscription only sees new blobs.
Control: GET /health, GET /_stub/deliveries, POST /_stub/replay on --port.
"""

import argparse
import json
import os
import queue
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import deque
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "eventgrid"
TOPIC = (
    "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/local"
    "/providers/Microsoft.Storage/storageAccounts/{account}"
)
NO_RETRY = {400, 413}


def log(source: str, line: str) -> None:
    print(f"{datetime.now():%H:%M:%S} {source:<17} {line}", flush=True)


def subject_for(container: str, name: str) -> str:
    return f"/blobServices/default/containers/{container}/blobs/{name}"


def blob_created_event(
    *, account: str, blob_endpoint: str, container: str, name: str, etag: str, size: int, content_type: str | None
) -> dict:
    """One BlobCreated event in the Event Grid schema (what a system topic on a storage account sends)."""
    url = f"{blob_endpoint.rstrip('/')}/{container}/{urllib.parse.quote(name)}"
    return {
        "topic": TOPIC.format(account=account),
        "subject": subject_for(container, name),
        "eventType": "Microsoft.Storage.BlobCreated",
        "id": str(uuid.uuid4()),
        "data": {
            "api": "PutBlob",
            "clientRequestId": str(uuid.uuid4()),
            "requestId": str(uuid.uuid4()),
            "eTag": etag.strip('"'),
            "contentType": content_type or "application/octet-stream",
            "contentLength": size,
            "blobType": "BlockBlob",
            "url": url,
            "sequencer": f"{time.time_ns():032x}",
            "storageDiagnostics": {"batchId": str(uuid.uuid4())},
        },
        "dataVersion": "",
        "metadataVersion": "1",
        "eventTime": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f0Z"),
    }


def matches(subscription: dict, event: dict) -> bool:
    types = subscription.get("includedEventTypes")
    return (
        (not types or event["eventType"] in types)
        and event["subject"].startswith(subscription.get("subjectBeginsWith", ""))
        and event["subject"].endswith(subscription.get("subjectEndsWith", ""))
    )


def changed(seen: dict[str, str], listing: dict[str, str]) -> list[str]:
    """Names in `listing` (name -> ETag) that are new or whose ETag differs from `seen`, in name order."""
    return sorted(name for name, etag in listing.items() if seen.get(name) != etag)


def post(endpoint: str, body: object, event_type: str, timeout: float, delivery: int = 1) -> tuple[int, bytes]:
    """POST like Event Grid does. Returns (status, body); status 0 = no connection."""
    data = json.dumps(body).encode()
    request = urllib.request.Request(endpoint, data=data, method="POST")  # noqa: S310 (configured local URL)
    request.add_header("Content-Type", "application/json")
    request.add_header("aeg-event-type", event_type)
    request.add_header("aeg-delivery-count", str(delivery - 1))  # Event Grid counts earlier attempts
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (configured local URL)
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return 0, b""


def validate(endpoint: str, timeout: float) -> bool:
    """The Event Grid schema's subscription validation handshake: the endpoint must echo the code back."""
    code = str(uuid.uuid4())
    event = {
        "id": str(uuid.uuid4()),
        "topic": TOPIC.format(account="devstoreaccount1"),
        "subject": "",
        "eventType": "Microsoft.EventGrid.SubscriptionValidationEvent",
        "data": {"validationCode": code, "validationUrl": None},
        "dataVersion": "2",
        "metadataVersion": "1",
        "eventTime": datetime.now(UTC).isoformat(),
    }
    status, body = post(endpoint, [event], "SubscriptionValidation", timeout)
    if status != 200:
        return False
    try:
        return json.loads(body).get("validationResponse") == code
    except (json.JSONDecodeError, AttributeError):
        return False


def queue_destination(config: dict) -> str | None:
    """The queue name of a storage queue subscription (D55), None for a webhook one."""
    destination = config.get("destination") or {}
    if not destination:
        return None
    if destination.get("type") != "storageQueue" or not destination.get("queueName"):
        raise SystemExit(f"subscription {config['name']}: destination must be a storageQueue with a queueName")
    return destination["queueName"]


class QueueSender:
    """Event Grid's storage queue handler: one event per message, base64 (the queue trigger's default encoding)."""

    def __init__(self, queue_name: str, connection: str) -> None:
        from azure.storage.queue import QueueClient, TextBase64EncodePolicy

        self.client = QueueClient.from_connection_string(
            connection, queue_name, message_encode_policy=TextBase64EncodePolicy()
        )

    def __call__(self, event: dict) -> int:
        try:
            self.client.send_message(json.dumps(event))
        except Exception:  # Azurite down, queue missing: retried like a webhook that didn't answer
            return 0
        return 201


class Subscription:
    def __init__(self, config: dict, delays: list[float], record: deque, sender=None) -> None:
        self.name = config["name"]
        self.config = config
        self.delays = delays
        self.record = record
        self.events: queue.Queue = queue.Queue()
        self.queue_name = queue_destination(config)
        if self.queue_name and sender is None:
            connection = os.getenv("QUEUE_CONN") or os.getenv("BLOB_CONN", "UseDevelopmentStorage=true")
            sender = QueueSender(self.queue_name, connection)
        self.sender = sender
        self.validated = self.queue_name is not None  # a queue needs no handshake

    def _send(self, event: dict, attempt: int) -> int:
        if self.sender is not None:
            return self.sender(event)
        status, _ = post(
            self.config["endpoint"], [event], "Notification", self.config.get("timeoutSeconds", 30), attempt
        )
        return status

    def start(self) -> "Subscription":
        threading.Thread(target=self._run, daemon=True).start()
        return self

    def _handshake(self) -> None:
        endpoint, started, told = self.config["endpoint"], time.monotonic(), False
        while not validate(endpoint, self.config.get("timeoutSeconds", 30)):
            if not told:
                log(self.name, "validation handshake: waiting for the Functions host (func start)")
                told = True
            time.sleep(3)
        self.validated = True
        log(self.name, f"validated: the endpoint answered the handshake ({time.monotonic() - started:.0f} s)")

    def _run(self) -> None:
        if not self.validated:
            self._handshake()
        while True:
            self._deliver(self.events.get())

    def _deliver(self, event: dict) -> None:
        short, limit = event["id"][:8], self.config.get("maxDeliveryAttempts", 30)
        status = 0
        for attempt in range(1, limit + 1):
            status = self._send(event, attempt)
            if 200 <= status <= 204:
                log(self.name, f"{short} delivered: HTTP {status} (attempt {attempt})")
                self._remember(event, "delivered", status, attempt)
                return
            if status in NO_RETRY or attempt == limit:
                break
            delay = self.delays[min(attempt - 1, len(self.delays) - 1)]
            log(self.name, f"{short} attempt {attempt} got {status or 'no connection'}, retry in {delay:g} s")
            time.sleep(delay)
        target = DATA / "deadletter" / self.name / f"{event['id']}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"event": event, "lastStatus": status, "attempts": attempt}, indent=2) + "\n")
        log(
            self.name,
            f"{short} DEAD-LETTERED after {attempt} attempt(s), last {status or 'no connection'}: "
            f"{target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}",
        )
        self._remember(event, "dead-lettered", status, attempt)

    def _remember(self, event: dict, result: str, status: int, attempts: int) -> None:
        self.record.append(
            {
                "id": event["id"],
                "subscription": self.name,
                "subject": event["subject"],
                "eTag": event["data"]["eTag"],
                "result": result,
                "status": status,
                "attempts": attempts,
                "at": datetime.now(UTC).isoformat(timespec="seconds"),
            }
        )


class Stub:
    def __init__(self, config: dict, state_file: Path, reset: bool) -> None:
        from azure.storage.blob import BlobServiceClient

        self.config = config
        self.source = config["source"]
        self.service = BlobServiceClient.from_connection_string(os.getenv("BLOB_CONN", "UseDevelopmentStorage=true"))
        self.state_file = state_file
        self.record: deque = deque(maxlen=200)
        self.sent: deque = deque(maxlen=200)  # events sent to at least one subscription (for replay)
        self.subscriptions = [
            Subscription(s, config["retryDelaysSeconds"], self.record) for s in config["subscriptions"]
        ]
        self.seen = {} if reset else self._load()
        self.first = reset or not state_file.is_file()

    def _load(self) -> dict:
        try:
            return json.loads(self.state_file.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    def _save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.seen, indent=1, sort_keys=True) + "\n")

    def _listing(self) -> dict[str, tuple[str, int, str | None]]:
        found = {}
        for container in self.source["containers"]:
            client = self.service.get_container_client(container)
            if not client.exists():
                continue
            for blob in client.list_blobs():
                found[f"{container}/{blob.name}"] = (blob.etag, blob.size, blob.content_settings.content_type)
        return found

    def scan(self) -> None:
        listing = self._listing()
        etags = {key: value[0] for key, value in listing.items()}
        if self.first:
            self.seen, self.first = etags, False
            self._save()
            log("stub", f"first start: {len(etags)} existing blob(s) recorded, no events for them")
            return
        new = changed(self.seen, etags)
        for key in new:
            container, name = key.split("/", 1)
            etag, size, content_type = listing[key]
            event = blob_created_event(
                account=self.source["account"],
                blob_endpoint=self.service.url,
                container=container,
                name=name,
                etag=etag,
                size=size,
                content_type=content_type,
            )
            targets = [s for s in self.subscriptions if matches(s.config, event)]
            log("event", f"{event['id'][:8]} BlobCreated {key}" + ("" if targets else "  (no subscription matches)"))
            for subscription in targets:
                subscription.events.put(event)
            if targets:
                self.sent.append(event)
        removed = set(self.seen) - set(etags)
        if new or removed:
            self.seen = etags
            self._save()

    def replay(self, subject_endswith: str) -> dict | None:
        for event in reversed(self.sent):
            if event["subject"].endswith(subject_endswith):
                for subscription in self.subscriptions:
                    if matches(subscription.config, event):
                        subscription.events.put(event)
                log("event", f"{event['id'][:8]} replayed (same event id): {event['subject'].rsplit('/blobs/', 1)[1]}")
                return event
        return None

    def watch(self) -> None:
        while True:
            try:
                self.scan()
            except Exception as exc:  # Azurite restarting: keep the stub up and say so
                log("stub", f"scan failed: {type(exc).__name__}; retrying")
            time.sleep(self.source.get("pollSeconds", 1))


def serve(stub: Stub, port: int) -> None:
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: object) -> None:
            data = json.dumps(body, indent=2).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/health":
                self._send(200, {"status": "ok", "validated": {s.name: s.validated for s in stub.subscriptions}})
            elif self.path == "/_stub/deliveries":
                self._send(200, list(stub.record))
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/_stub/replay":
                self._send(404, {"error": "not found"})
                return
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")
                suffix = body["subject_endswith"]
            except (ValueError, KeyError, TypeError):
                self._send(400, {"error": 'expected {"subject_endswith": "..."}'})
                return
            event = stub.replay(suffix)
            if event is None:
                self._send(404, {"error": "no event sent for a subject ending like that"})
            else:
                self._send(202, {"replayed": event["id"], "subject": event["subject"]})

        def log_message(self, *args):
            pass

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=ROOT / "emulators" / "eventgrid" / "subscriptions.json")
    parser.add_argument("--port", type=int, default=6100)
    parser.add_argument("--state", type=Path, default=DATA / "state.json")
    parser.add_argument("--reset", action="store_true", help="forget the seen ETags: existing blobs send nothing")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    stub = Stub(config, args.state, args.reset)
    threading.Thread(target=serve, args=(stub, args.port), daemon=True).start()
    containers = ", ".join(config["source"]["containers"])
    log(
        "stub",
        f"watching {config['source']['account']}/{containers} every {config['source'].get('pollSeconds', 1)} s, "
        f"{len(stub.subscriptions)} subscription(s), control on http://127.0.0.1:{args.port}",
    )
    for subscription in stub.subscriptions:
        subscription.start()
    try:
        stub.watch()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
