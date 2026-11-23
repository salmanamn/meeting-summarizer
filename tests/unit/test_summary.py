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
        {"open_questions": [{"question": "q", "evidence": None}] * 61},
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
    assert warnings == ["action_items[0]: owner 'Priya' is not named where the task is said, removed"]


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
    """The decision holds all of the action's words, but it is said elsewhere (and says as much of that line)."""
    s = summary(decisions=[{"text": "Release on 15 March and send the numbers.", "evidence": "00:13"}])
    grounded, warnings = ground(s, transcript)
    assert [d.evidence for d in grounded.decisions] == ["00:13"] and warnings == []


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


def test_evidence_moves_to_the_line_that_says_the_item(transcript):
    """M3 runs: M04 cited 00:00 for every item, M01 a time one line off (D29)."""
    s = summary(
        decisions=[{"text": "We release on the fifteenth of March.", "evidence": "00:00"}],
        action_items=[{"task": "Send the numbers by Wednesday", "owner": "Omar", "due": None, "evidence": None}],
        open_questions=[{"question": "Who presents at the all hands?", "evidence": "09:59"}],
    )
    grounded, warnings = ground(s, transcript)
    assert grounded.decisions[0].evidence == "00:13"
    assert grounded.action_items[0].evidence == "00:00"
    assert grounded.open_questions[0].evidence == "01:15"
    assert warnings == [
        "action_items[0]: evidence missing, set to '00:00'",
        "decisions[0]: evidence '00:00' (a line that says less of it) moved to '00:13'",
        "open_questions[0]: evidence '09:59' (not inside any segment) moved to '01:15'",
    ]


def test_evidence_stays_when_no_line_says_more(transcript):
    s = summary(decisions=[{"text": "Book a room.", "evidence": "00:07"}])  # no line shares two words with it
    grounded, warnings = ground(s, transcript)
    assert grounded.decisions[0].evidence == "00:07" and warnings == []


def test_the_owner_must_be_named_near_the_task(transcript):
    """M3 runs: models gave "I will update the release notes" to an attendee nobody named there (D29)."""
    s = summary(
        action_items=[
            {"task": "Ask who presents at the all hands", "owner": "Omar", "due": None, "evidence": "01:15"},
            {"task": "Send the numbers", "owner": "Omar", "due": None, "evidence": "00:07"},
        ]
    )
    grounded, warnings = ground(s, transcript, attendees=("Omar", "Sara"))
    assert [a.owner for a in grounded.action_items] == [None, "Omar"]  # 01:15 is 3 segments after "Omar, ..."
    assert "action_items[0]: owner 'Omar' is not named where the task is said, removed" in warnings


def test_digits_and_number_words_are_the_same_words():
    """A model writes "April 9th" where Whisper wrote "the ninth of April" (M04, D29)."""
    from meeting.words import content_words, number_word

    assert [number_word(w) for w in ["9th", "15", "1st", "21st", "20th", "30", "2026", "next"]] == [
        "ninth",
        "fifteen",
        "first",
        "twenty first",
        "twentieth",
        "thirty",
        "2026",
        "next",
    ]
    assert content_words("Launch on April 9th") <= content_words("We launch the new website on the ninth of April")


def test_the_line_where_the_task_is_given_wins(transcript):
    """M3 runs: "Get new icons approved by Friday" cited at the line that only mentions the icons; the owner's name
    and the deadline count as words of the task, so "Lina, can you get the new icons approved by Friday?" wins,
    and the owner stays (D32). Here: "Omar, please send the numbers by Wednesday" over "Sure, I will send them"."""
    s = summary(
        action_items=[{"task": "Send the numbers", "owner": "Omar", "due": "by Wednesday", "evidence": "00:07"}]
    )
    grounded, warnings = ground(s, transcript)
    assert (grounded.action_items[0].evidence, grounded.action_items[0].owner) == ("00:00", "Omar")
    assert warnings == ["action_items[0]: evidence '00:07' (a line that says less of it) moved to '00:00'"]


def test_among_equal_lines_the_nearest_to_the_cited_time_wins():
    """M3 round 3 (granite4, M06): "The customer demo will be held on Wednesday" moved to the opening line about
    "the customer demo" instead of "The demo stays on Wednesday" next to the cited time (D32)."""
    from factories import make_transcript

    t = make_transcript(
        (0, 4, "Two things today: the customer demo and our release rhythm."),
        (5, 9, "I suggest we move it to Thursday."),
        (10, 14, "Thursday is bad for the customer."),
        (15, 18, "Yes. The demo stays on Wednesday."),
    )
    s = summary(decisions=[{"text": "Demo on Wednesday, for the customer", "evidence": "00:10"}], action_items=[])
    assert ground(s, t)[0].decisions[0].evidence == "00:15"  # 2 words each with 00:00; 00:15 is nearer


def test_the_attendee_addressed_just_before_becomes_the_owner():
    """M3 runs (M04): "Hana, the figures on page two ... are from last year." then "You are right. I will update the
    figures ... by Tuesday."; models wrote Yusuf or nobody (D32)."""
    from factories import make_transcript

    t = make_transcript(
        (0, 6, "Hello Yusuf, hello Hana."),
        (20, 26, "Hana, the figures on page two of the budget sheet are from last year."),
        (27, 28, "You are right."),
        (29, 34, "I will update the figures on page two of the budget sheet by Tuesday."),
        (35, 38, "And I will check the ad prices with the agency."),
    )
    s = summary(
        decisions=[],
        action_items=[
            {"task": "Update the budget figures", "owner": "Yusuf", "due": "by Tuesday", "evidence": "00:00"},
            {"task": "Check the ad prices", "owner": "Yusuf", "due": None, "evidence": "00:35"},
        ],
    )
    grounded, warnings = ground(s, t, attendees=("Noor", "Yusuf", "Hana"))
    assert [(a.evidence, a.owner) for a in grounded.action_items] == [("00:29", "Hana"), ("00:35", None)]
    assert "action_items[0]: owner set to 'Hana', addressed where the task is given" in warnings


def test_an_address_about_another_task_gives_no_owner():
    """Like H01: "Omar, please get two quotes from other vendors." / "I will have two quotes ..." / "I will write
    to the current vendor about the delays." The third is someone else's task: no owner (D32)."""
    from factories import make_transcript

    t = make_transcript(
        (0, 4, "Omar, please get two quotes from other vendors by the end of the month."),
        (5, 8, "I will have two quotes by the end of the month."),
        (9, 12, "I will write to the current vendor about the delays."),
    )
    s = summary(
        decisions=[],
        action_items=[
            {"task": "Write to the vendor about the delays", "owner": None, "due": None, "evidence": "00:09"}
        ],
        open_questions=[],
    )
    grounded, warnings = ground(s, t, attendees=("Sara", "Omar", "Lina"))
    assert grounded.action_items[0].owner is None and warnings == []


def test_evidence_does_not_move_to_an_agenda_line_far_away():
    """M3 round 2 (M05, M06): items moved to the opening line that lists the topics (D31)."""
    from factories import make_transcript

    t = make_transcript(
        (0, 8, "Three topics today: the training, the articles and the rota."),
        (100, 104, "Nice weather today."),
        (110, 116, "Who will run the training for the refunds?"),
    )
    s = summary(
        decisions=[],
        action_items=[],
        open_questions=[{"question": "Who runs the refund training?", "evidence": "01:40"}],
    )
    grounded, warnings = ground(s, t)
    assert grounded.open_questions[0].evidence == "01:50"  # within 60 s of the cited line, not 00:00
    assert warnings == ["open_questions[0]: evidence '01:40' (a line that says less of it) moved to '01:50'"]


@pytest.mark.parametrize(
    "text",
    ["Demo recording is an idea, not decided", "Release rhythm discussion postponed", "Weekly releases not yet agreed"],
)
def test_a_decision_that_says_it_was_not_decided_is_removed(transcript, text):
    """M3 round 2: granite4 listed "Demo recording is an idea, not decided" as a decision (M06's forbidden item)."""
    grounded, warnings = ground(summary(decisions=[{"text": text, "evidence": "00:13"}]), transcript)
    assert grounded.decisions == [] and warnings == ["decisions[0]: says it was not decided, removed"]
