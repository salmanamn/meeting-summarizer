"""The queue trigger's message (D55): an Event Grid BlobCreated event, as an Event Grid subscription with a storage
queue destination writes it (Event Grid schema, one event per message). The job needs only the manifest's name."""

import json

EVENTS_QUEUE = "meeting-events"
BLOB_CREATED = "Microsoft.Storage.BlobCreated"
MANIFEST_SUFFIX = "/meeting.json"


def manifest_name(body: str, container: str) -> str | None:
    """'<container>/<id>/meeting.json' for a BlobCreated event on a manifest in `container`, else None.

    Accepts the event alone or a batch of exactly one (what a webhook gets). Anything else (not JSON, another
    event type, another container, a recording or an attachment) is None: retrying it can't help, so the function
    logs it and completes the message.
    """
    try:
        event = json.loads(body)
    except (TypeError, ValueError):
        return None
    if isinstance(event, list):
        event = event[0] if len(event) == 1 else None
    if not isinstance(event, dict) or event.get("eventType") != BLOB_CREATED:
        return None
    subject = event.get("subject")
    prefix = f"/blobServices/default/containers/{container}/blobs/"
    if not isinstance(subject, str) or not subject.startswith(prefix) or not subject.endswith(MANIFEST_SUFFIX):
        return None
    return f"{container}/{subject[len(prefix) :]}"
