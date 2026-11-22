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
    """The schema the model sees and the Pydantic models that check its answer must not drift apart. With
    attachments every item has a `source`; without, the schema leaves it out and the model's default is None."""
    with_refs = summary_schema(["00:00"], ["agenda.docx #1"])
    assert list(with_refs["properties"]) == list(MeetingSummary.model_fields)
    for kind, model in (("decisions", Decision), ("action_items", ActionItem), ("open_questions", OpenQuestion)):
        assert list(with_refs["properties"][kind]["items"]["properties"]) == list(model.model_fields), kind
        without = list(SCHEMA["properties"][kind]["items"]["properties"])
        assert without == [f for f in model.model_fields if f != "source"], kind


def test_a_source_can_only_be_an_attachment_block_or_null():
    schema = summary_schema(["00:00"], ["agenda.docx #1", "budget.pdf p2.1"])
    sources = [n for p, n in walk(schema) if p.endswith(".source")]
    assert len(sources) == 3
    for node in sources:
        assert node == {"anyOf": [{"type": "string", "enum": ["agenda.docx #1", "budget.pdf p2.1"]}, {"type": "null"}]}
    assert not [p for p, _ in walk(SCHEMA) if p.endswith(".source")]  # no attachments: no source field at all


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
        {"action_items": [{"task": "x", "owner": "o" * 401, "due": None, "evidence": None}]},
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


@pytest.mark.parametrize(
    ("due", "kept"),
    [
        ("Wednesday", "Wednesday"),
        ("by Wednesday", "by Wednesday"),
        ("wednesday.", "wednesday."),
        ("Wednesday Next, the 15th of March (00:27 mentioned as 'Wednesday')", "Wednesday"),  # M1 phi4-mini, D28
        ("By Wednesday from the meeting date", "By Wednesday"),  # M3 run 2
        ("No specific due date mentioned", None),  # M3 run 2: a comment, no deadline
        ("2026-03-11", None),  # a date the model worked out
        ("Friday", None),  # not said in this meeting
    ],
)
def test_due_keeps_only_the_meetings_own_words(transcript, due, kept):
    s = summary(action_items=[{"task": "Send the numbers.", "owner": "Omar", "due": due, "evidence": "00:00"}])
    grounded, warnings = ground(s, transcript)
    assert grounded.action_items[0].due == kept
    assert bool(warnings) is (kept != due)


def test_a_decision_that_repeats_an_action_item_is_removed(transcript):
    """M1/M2 runs: phi4-mini listed "Update the release notes" as a decision and an action item, same time."""
    s = summary(
        decisions=[
            {"text": "Send the numbers to the team by Wednesday.", "evidence": "00:00"},
            {"text": "Release on 15 March.", "evidence": "00:13"},
        ]
    )
    grounded, warnings = ground(s, transcript)
    assert [d.text for d in grounded.decisions] == ["Release on 15 March."]
    assert warnings == ["decisions[0]: repeats the action item at 00:00, removed"]


def test_similar_words_at_another_time_are_two_items(transcript):
    s = summary(decisions=[{"text": "Send the numbers to the team.", "evidence": "00:07"}])
    assert len(ground(s, transcript)[0].decisions) == 1


def test_a_source_outside_the_attachments_is_removed(transcript):
    s = summary(decisions=[{"text": "Release on 15 March.", "evidence": "00:13", "source": "agenda.docx #9"}])
    grounded, warnings = ground(s, transcript, refs=("agenda.docx #1",))
    assert grounded.decisions[0].source is None
    assert warnings == ["decisions[0]: source 'agenda.docx #9' is not an attachment block, removed"]
    kept, none = ground(s, transcript, refs=("agenda.docx #9",))
    assert kept.decisions[0].source == "agenda.docx #9" and none == []


def test_a_long_due_is_grounded_not_a_broken_summary(transcript):
    """M3 run 1: phi4-mini wrote a `due` over 80 characters and the whole summary was refused (M06, ES2002b)."""
    long_due = "Wednesday, which is when the team expects the numbers, as discussed at the start of the meeting " * 2
    s = summary(action_items=[{"task": "Send the numbers.", "owner": "Omar", "due": long_due, "evidence": "00:00"}])
    grounded, warnings = ground(s, transcript)
    assert grounded.action_items[0].due == "Wednesday"
    assert warnings[0].startswith("action_items[0]: due ") and warnings[0].endswith(
        "cut to the meeting's words 'Wednesday'"
    )


def test_a_decision_that_says_who_does_a_task_is_that_task(transcript):
    """M3 run 2 (M06): "Demo account preparation assigned to Yusuf by Tuesday" next to the action "Prepare demo
    account", same time: the action's words are all in the decision (D28)."""
    s = summary(
        decisions=[{"text": "Numbers sending assigned to Omar, due Wednesday.", "evidence": "00:00"}],
        action_items=[{"task": "Send the numbers", "owner": "Omar", "due": None, "evidence": "00:00"}],
    )
    grounded, warnings = ground(s, transcript)
    assert grounded.decisions == [] and warnings == ["decisions[0]: repeats the action item at 00:00, removed"]
