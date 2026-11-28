"""The Functions app (M2): the manifest's BlobCreated event starts a meeting job; an HTTP endpoint reports it.

Kept thin on purpose: everything that decides something is in `meeting.job` and is unit-tested without a host.
"""

import json
import logging
import re
from functools import lru_cache

import azure.functions as func

from meeting.events import EVENTS_QUEUE, manifest_name
from meeting.job import JobRunner, public_view
from meeting.llm import JsonModel
from meeting.manifest import MEETING_ID_PATTERN
from meeting.settings import load, trigger
from meeting.stores import BlobStore, JobStore

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
log = logging.getLogger("meeting.function")
# The Azure SDKs log every HTTP request and response at INFO (azure.core's HttpLoggingPolicy): in M7 they were most
# of AppTraces and pushed the job's own lines out of a 60-row query (D51). Warnings and errors still come through.
logging.getLogger("azure").setLevel(logging.WARNING)


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
    """STT_ENGINE (D44): Azure AI Speech batch transcription on Azure (SPEECH_ENDPOINT set), Whisper on the laptop.
    Either is made once per worker process, on the first job (Whisper's model takes a few seconds to load)."""
    settings = load()
    if settings.stt_engine == "speech":
        from meeting.speech import SpeechTranscriber

        return SpeechTranscriber.from_settings(settings)
    from meeting.stt import WhisperTranscriber

    return WhisperTranscriber.from_settings(settings)


@lru_cache(maxsize=1)
def _model() -> JsonModel:
    return JsonModel.from_settings(load())


if trigger() == "queue":
    # D55 (a container on a cluster, Project 7): Event Grid writes the manifest's BlobCreated event into a storage
    # queue, the host pulls it. Outbound only, so it works behind private endpoints, and KEDA scales on the queue.
    @app.queue_trigger(arg_name="msg", queue_name=EVENTS_QUEUE, connection="RecordingsStorage")
    def meeting_queue_job(msg: func.QueueMessage) -> None:
        """Any exception makes the host retry the message, up to maxDequeueCount (host.json), then it moves to the
        queue `meeting-events-poison`; the job records its own last attempt. An event that names no manifest is
        logged and completed: retrying it can't help."""
        name = manifest_name(msg.get_body().decode("utf-8", errors="replace"), load().incoming_container)
        if name is None:
            log.warning("meeting event %s ignored: not a BlobCreated event for a manifest", msg.id)
            return
        outcome = _runner().handle(name)
        log.info("meeting job %s: %s (%s)", outcome.meeting_id or name, outcome.status, outcome.detail)

else:
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
