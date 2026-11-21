"""The summary contract: the schema sent to the model, the limits enforced after, and grounding (D4)."""

import json

import pytest
from pydantic import ValidationError

from meeting.summary import ActionItem, Decision, MeetingSummary, OpenQuestion, ground, summary_schema

SCHEMA = summary_schema(["00:00", "00:07", "00:13", "00:13", "01:15"])


def walk(schema: dict, path: str = "$"):
    yield path, schema
    for name, sub in schema.get("properties", {}).items():
        yield from walk(sub, f"{path}.{name}")
    if "items" in schema:
        yield from walk(schema["items"], f"{path}[]")
    for i, sub in enumerate(schema.get("anyOf", [])):
        yield from walk(sub, f"{path}|{i}")


def test_schema_is_in_the_strict_subset():
    """Every object: all properties required, no extra properties. No keyword strict mode rejects."""
    rejected = {"minLength", "maxLength", "minItems", "maxItems", "pattern", "format", "default", "$ref", "oneOf"}
    for path, node in walk(SCHEMA):
        assert not rejected & node.keys(), path
        if node.get("type") == "object":
            assert node["additionalProperties"] is False, path
            assert node["required"] == list(node["properties"]), path


def test_schema_and_models_name_the_same_fields():
    """The schema the model sees and the Pydantic models that check its answer must not drift apart."""
    pairs = [
        (SCHEMA, MeetingSummary),
        (SCHEMA["properties"]["decisions"]["items"], Decision),
        (SCHEMA["properties"]["action_items"]["items"], ActionItem),
        (SCHEMA["properties"]["open_questions"]["items"], OpenQuestion),
    ]
    for schema, model in pairs:
        assert list(schema["properties"]) == list(model.model_fields), model.__name__


def test_nullable_strings_are_exactly_owner_and_due():
    nullable = {p for p, n in walk(SCHEMA) if n.get("type") == ["string", "null"]}
    assert nullable == {
        "$.action_items[].owner",
        "$.action_items[].due",
    }
    assert json.dumps(SCHEMA)  # serialisable as sent


def test_evidence_can_only_be_a_segment_time_or_null():
    """D14: phi4-mini wrote quotes into evidence when it was a free string; now the grammar allows only these."""
    evidence = [n for p, n in walk(SCHEMA) if p.endswith(".evidence")]
    assert len(evidence) == 3
    for node in evidence:
        assert node == {"anyOf": [{"type": "string", "enum": ["00:00", "00:07", "00:13", "01:15"]}, {"type": "null"}]}


def test_a_schema_needs_segment_times():
    with pytest.raises(ValueError, match="at least one segment time"):
        summary_schema([])


def summary(**changes) -> MeetingSummary:
    data = {
        "title": "Release planning",
        "overview": "The team planned the release.",
        "decisions": [{"text": "Release on 15 March.", "evidence": "00:13"}],
        "action_items": [{"task": "Send the numbers.", "owner": "Omar", "due": "Wednesday", "evidence": "00:00"}],
        "open_questions": [{"question": "Who presents at the all hands?", "evidence": "01:15"}],
    }
    data.update(changes)
    return MeetingSummary.model_validate(data)


def test_a_valid_summary_and_empty_lists():
    assert summary().action_items[0].owner == "Omar"
    empty = summary(decisions=[], action_items=[], open_questions=[])
    assert (empty.decisions, empty.action_items, empty.open_questions) == ([], [], [])


@pytest.mark.parametrize(
    "changes",
    [
        {"title": ""},
        {"title": "x" * 81},
        {"overview": "  "},
        {"decisions": [{"text": "x"}]},  # evidence missing: required, even when null
        {"decisions": [{"text": "x", "evidence": None, "extra": 1}]},
        {"action_items": [{"task": "x", "owner": "o" * 81, "due": None, "evidence": None}]},
        {"open_questions": [{"question": "q", "evidence": None}] * 21},
        {"surprise": True},
    ],
)
def test_limits_and_unknown_fields_are_rejected(changes):
    with pytest.raises(ValidationError):
        summary(**changes)


def test_grounding_keeps_what_the_transcript_supports(transcript):
    grounded, warnings = ground(summary(), transcript)
    assert warnings == []
    assert grounded == summary()


def test_grounding_removes_an_owner_nobody_named(transcript):
    s = summary(action_items=[{"task": "Book the room.", "owner": "Priya", "due": None, "evidence": "00:07"}])
    grounded, warnings = ground(s, transcript)
    assert grounded.action_items[0].owner is None
    assert grounded.action_items[0].task == "Book the room."  # the item stays; only the invented owner goes
    assert warnings == ["action_items[0]: owner 'Priya' is not named in the transcript, removed"]


def test_an_attendee_counts_as_named(transcript):
    s = summary(action_items=[{"task": "Book the room.", "owner": "Priya", "due": None, "evidence": None}])
    grounded, warnings = ground(s, transcript, attendees=("Priya", "Omar"))
    assert grounded.action_items[0].owner == "Priya"
    assert warnings == []


@pytest.mark.parametrize(("owner", "kept"), [("omar", True), ("OMAR", True), ("Om", False), ("Omar Haddad", False)])
def test_owner_must_be_a_whole_name_in_the_transcript(transcript, owner, kept):
    s = summary(action_items=[{"task": "t", "owner": owner, "due": None, "evidence": None}])
    assert (ground(s, transcript)[0].action_items[0].owner is not None) is kept


@pytest.mark.parametrize("evidence", ["00:40", "09:99", "soon", "1:00:00"])
def test_grounding_removes_evidence_outside_every_segment(transcript, evidence):
    s = summary(decisions=[{"text": "x", "evidence": evidence}])
    grounded, warnings = ground(s, transcript)
    assert grounded.decisions[0].evidence is None
    assert warnings == [f"decisions[0]: evidence {evidence!r} is not inside any segment, removed"]
