"""The Functions app (M2): the manifest's BlobCreated event starts a meeting job; an HTTP endpoint reports it.

Kept thin on purpose: everything that decides something is in `meeting.job` and is unit-tested without a host.
"""

import json
import logging
import re
from functools import lru_cache

import azure.functions as func

from meeting.job import JobRunner, public_view
from meeting.llm import JsonModel
from meeting.manifest import MEETING_ID_PATTERN
from meeting.settings import load
from meeting.stores import BlobStore, JobStore

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
log = logging.getLogger("meeting.function")


@lru_cache(maxsize=1)
def _runner() -> JobRunner:
    settings = load()
    return JobRunner(
        settings,
        BlobStore.from_settings(settings),
        JobStore.from_settings(settings),
        transcriber=_transcriber,
        model=_model,
    )


@lru_cache(maxsize=1)
def _transcriber():
    """Whisper is loaded once per worker process, on the first job (a few seconds), not on every delivery."""
    from meeting.stt import WhisperTranscriber

    return WhisperTranscriber.from_settings(load())


@lru_cache(maxsize=1)
def _model() -> JsonModel:
    return JsonModel.from_settings(load())


# D12/D15: Flex Consumption has only the Event Grid-based Blob trigger. The path matches manifests only, and the
# Event Grid subscription filters on the same suffix, so a 300 MB recording never reaches the worker.
@app.blob_trigger(
    arg_name="manifest",
    path="incoming/{meeting_id}/meeting.json",
    connection="RecordingsStorage",
    source=func.BlobSource.EVENT_GRID,
)
def meeting_job(manifest: func.InputStream) -> None:
    """Any exception makes the host retry the delivery at once, up to poisonBlobThreshold (host.json), then the
    message goes to the poison queue `webjobs-blobtrigger-poison`; the job records its own last attempt."""
    outcome = _runner().handle(manifest.name)
    log.info("meeting job %s: %s (%s)", outcome.meeting_id or manifest.name, outcome.status, outcome.detail)


@app.route(route="meetings/{meeting_id}", methods=["GET"])
def meeting_status(req: func.HttpRequest) -> func.HttpResponse:
    meeting_id = req.route_params.get("meeting_id", "")
    if not re.fullmatch(MEETING_ID_PATTERN, meeting_id):
        return _json({"error": "invalid meeting id"}, 400)
    doc = _runner().jobs.get(meeting_id)
    if doc is None:
        return _json({"error": "no job for this meeting id"}, 404)
    return _json(public_view(doc), 200)


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    return _json({"status": "ok"}, 200)


def _json(body: dict, status: int) -> func.HttpResponse:
    return func.HttpResponse(json.dumps(body, ensure_ascii=False), status_code=status, mimetype="application/json")
