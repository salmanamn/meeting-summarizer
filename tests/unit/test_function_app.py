"""The Functions app's contract: which functions exist, how they are triggered, and the status endpoint."""

import json
from pathlib import Path

import azure.functions as func
import pytest
from fakes import FakeJobs

import function_app
from meeting.settings import load

SRC = Path(__file__).resolve().parents[2] / "src"


def bindings() -> dict[str, list[dict]]:
    return {fn.get_function_name(): fn.get_bindings_dict()["bindings"] for fn in function_app.app.get_functions()}


def test_the_functions_and_their_triggers():
    found = bindings()
    assert sorted(found) == ["health", "meeting_job", "meeting_status"]
    (trigger,) = found["meeting_job"]
    assert trigger["type"] == "blobTrigger"
    assert trigger["source"] == "EventGrid"  # Flex Consumption has no polling Blob trigger (D12, D15)
    assert trigger["path"] == "incoming/{meeting_id}/meeting.json"
    assert trigger["connection"] == "RecordingsStorage"
    status = found["meeting_status"][0]
    assert (status["route"], status["authLevel"].value) == ("meetings/{meeting_id}", "function")
    assert found["health"][0]["authLevel"].value == "anonymous"


def test_retry_limits_agree():
    """The job's own attempt count must stop where the host stops redelivering (poisonBlobThreshold)."""
    host = json.loads((SRC / "host.json").read_text())
    example = json.loads((SRC / "local.settings.json.example").read_text())["Values"]
    assert host["extensions"]["blobs"]["poisonBlobThreshold"] == load({}).job_max_attempts == 5
    assert int(example["JOB_MAX_ATTEMPTS"]) == 5
    assert host["extensions"]["blobs"]["maxDegreeOfParallelism"] == 1  # one Whisper per instance


def test_sdk_http_logging_stays_out_of_app_insights():
    """M7: the SDKs' INFO request/response dumps flooded AppTraces (D51). The Python worker's `azure` loggers and the
    host's `Azure.*` categories (its blob extension's storage client) log warnings and up; the job's own lines and
    the host's function telemetry stay at Information."""
    import logging

    assert logging.getLogger("azure").level == logging.WARNING
    assert not logging.getLogger("azure.core.pipeline.policies.http_logging_policy").isEnabledFor(logging.INFO)
    assert logging.getLogger("meeting.function").level == logging.NOTSET  # not raised: the job's own lines stay
    levels = json.loads((SRC / "host.json").read_text())["logging"]["logLevel"]
    assert levels == {"default": "Information", "Azure": "Warning"}


def test_local_settings_name_every_setting_the_code_reads():
    example = json.loads((SRC / "local.settings.json.example").read_text())["Values"]
    assert example["RecordingsStorage"] == example["AzureWebJobsStorage"] == "UseDevelopmentStorage=true"
    assert example["MODELS_DIR"] == "../models"  # func runs in src/


class Runner:
    def __init__(self, jobs):
        self.jobs = jobs


@pytest.fixture
def status(monkeypatch):
    jobs = FakeJobs()
    jobs.create({"id": "m01-1", "stage": "summarised", "attempts": 1})
    monkeypatch.setattr(function_app, "_runner", lambda: Runner(jobs))
    handler = function_app.meeting_status.build().get_user_function()

    def call(meeting_id: str) -> tuple[int, dict]:
        req = func.HttpRequest("GET", f"/api/meetings/{meeting_id}", body=b"", route_params={"meeting_id": meeting_id})
        response = handler(req)
        return response.status_code, json.loads(response.get_body())

    return call


def test_status_endpoint(status):
    code, body = status("m01-1")
    assert code == 200
    assert body == {"id": "m01-1", "stage": "summarised", "attempts": 1}  # no Cosmos system fields
    assert status("m09-9") == (404, {"error": "no job for this meeting id"})
    assert status("M01..") == (400, {"error": "invalid meeting id"})
