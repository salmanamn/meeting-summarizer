"""The CI stand-in model (scripts/fake_llm.py, D36): it answers the real client's real requests within the contract,
and refuses the requests a strict endpoint refuses."""

import json

import openai
import pytest
from factories import make_transcript
from fake_llm import FakeLLM, answer, minimal, strict_problems

from meeting.llm import JsonModel
from meeting.summarize import summarize
from meeting.summary import MeetingSummary, summary_schema


@pytest.fixture
def fake():
    server = FakeLLM().start()
    yield server
    server.stop()


def model(url: str) -> JsonModel:
    return JsonModel(base_url=url, api_key="ci", model="fake", reasoning_effort="none")


def test_a_summary_cites_the_longest_line_at_its_own_time(fake):
    transcript = make_transcript(
        (0.0, 2.0, "Hi Omar."),
        (3.0, 9.0, "We release version two on the fifteenth of March."),
        (10.0, 12.0, "Agreed, thanks."),
    )
    result = summarize(transcript, model(fake.url), attendees=("Omar",))
    assert [(d.text, d.evidence) for d in result.summary.decisions] == [
        ("We release version two on the fifteenth of March.", "00:03")
    ]
    assert result.summary.action_items == [] and result.summary.open_questions == []
    assert result.warnings == []  # grounding keeps it as it is
    sent = fake.requests[0]["response_format"]["json_schema"]
    assert sent["strict"] is True and sent["name"] == "meeting_summary"


def test_a_long_meeting_gets_parts_and_a_merge(fake):
    lines = [(i * 10.0, i * 10.0 + 8, f"Line {i} says the release plan item number {i} is settled.") for i in range(40)]
    result = summarize(make_transcript(*lines), model(fake.url), part_chars=600)
    assert result.parts > 1 and result.calls == result.parts + 1
    assert MeetingSummary.model_validate(result.summary.model_dump())


def test_a_model_error_is_an_http_error_for_the_client(fake):
    fake.next_status = [500]
    with pytest.raises(openai.InternalServerError):
        summarize(make_transcript((0.0, 3.0, "We decided it.")), model(fake.url))
    assert summarize(make_transcript((0.0, 3.0, "We decided it today.")), model(fake.url)).summary.decisions


def request(schema: dict, *, strict: bool = True) -> dict:
    spec = {"name": "meeting_summary", "strict": strict, "schema": schema}
    user = "<transcript>\n[00:00] We decided it.\n</transcript>"
    return {
        "messages": [{"role": "user", "content": user}],
        "response_format": {"type": "json_schema", "json_schema": spec},
    }


def test_requests_outside_the_strict_contract_are_refused():
    schema = summary_schema(["00:00"])
    assert answer(request(schema))[0] == 200
    assert answer({**request(schema), "response_format": {"type": "json_object"}})[0] == 400
    assert answer(request(schema, strict=False))[0] == 400
    loose = json.loads(json.dumps(schema))
    loose["properties"]["decisions"]["items"]["additionalProperties"] = True
    status, text = answer(request(loose))
    assert status == 400 and "additionalProperties" in text
    status, text = answer(request(summary_schema(["00:07"])))  # the transcript's time is not on offer
    assert status == 400 and "evidence enum" in text


def test_the_project_schemas_are_strict_and_have_a_minimal_instance():
    for schema in (summary_schema(["00:00", "00:05"]), summary_schema(["00:00"], ["agenda.docx #1"])):
        assert strict_problems(schema) == []
        assert MeetingSummary.model_validate(minimal(schema))
