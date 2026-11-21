"""The summary contract (D4): what the model must return, and the checks applied after it returns.

`summary_schema(stamps)` is sent with the request (`response_format: json_schema`, strict). It is built per
transcript: every `evidence` field may only be one of that transcript's segment times, or null (D14), so a model
cannot cite a quote or a time that does not exist. It stays inside the subset that Azure OpenAI's strict mode
accepts: every object lists all its properties as required and sets `additionalProperties: false`, optional values
are `["string", "null"]` or `anyOf` with null, `enum` for the times, and no length keywords. Lengths and counts are
enforced afterwards by the Pydantic models, and `ground()` checks the answer against the transcript again: every
evidence time must fall inside a segment, and every owner must be a name that was actually said.
"""

import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from meeting.transcript import Transcript, parse_stamp

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]
Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Decision(_Strict):
    text: Text
    evidence: str | None  # mm:ss of the segment where it was decided


class ActionItem(_Strict):
    task: Text
    owner: Short | None  # a person named in the meeting; None when nobody was named (D6)
    due: Short | None  # as said ("Friday", "end of March"); never a date the model worked out
    evidence: str | None


class OpenQuestion(_Strict):
    question: Text
    evidence: str | None


class MeetingSummary(_Strict):
    title: Short
    overview: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1200)]
    decisions: list[Decision] = Field(max_length=20)
    action_items: list[ActionItem] = Field(max_length=30)
    open_questions: list[OpenQuestion] = Field(max_length=20)


_NULLABLE = {"type": ["string", "null"]}
_STRING = {"type": "string"}


def _object(properties: dict) -> dict:
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def summary_schema(stamps: list[str]) -> dict:
    """The schema for one transcript: `stamps` are its segment times (mm:ss), the only values evidence may take."""
    if not stamps:
        raise ValueError("a summary schema needs at least one segment time")
    evidence = {"anyOf": [{"type": "string", "enum": list(dict.fromkeys(stamps))}, {"type": "null"}]}
    # Order matters for a model that writes left to right: the overview first, then the lists it summarises.
    return _object(
        {
            "title": _STRING,
            "overview": _STRING,
            "decisions": {"type": "array", "items": _object({"text": _STRING, "evidence": evidence})},
            "action_items": {
                "type": "array",
                "items": _object({"task": _STRING, "owner": _NULLABLE, "due": _NULLABLE, "evidence": evidence}),
            },
            "open_questions": {"type": "array", "items": _object({"question": _STRING, "evidence": evidence})},
        }
    )


def _named(name: str, text: str) -> bool:
    """The name, or every word of it, occurs as a whole word in the text (case ignored)."""
    words = re.findall(r"\w+", name.casefold())
    return bool(words) and all(re.search(rf"\b{re.escape(w)}\b", text) for w in words)


def ground(
    summary: MeetingSummary, transcript: Transcript, attendees: tuple[str, ...] = ()
) -> tuple[MeetingSummary, list[str]]:
    """Check the summary against the transcript. Returns a corrected copy and one warning per correction:
    evidence outside every segment becomes None; an owner who is neither named in the transcript nor an attendee
    becomes None."""
    known = " ".join([transcript.text, *attendees]).casefold()
    warnings: list[str] = []

    def check_evidence(kind: str, index: int, evidence: str | None) -> str | None:
        if evidence is None:
            return None
        seconds = parse_stamp(evidence)
        if seconds is None or not transcript.covers(seconds):
            warnings.append(f"{kind}[{index}]: evidence {evidence!r} is not inside any segment, removed")
            return None
        return evidence

    decisions = [
        d.model_copy(update={"evidence": check_evidence("decisions", i, d.evidence)})
        for i, d in enumerate(summary.decisions)
    ]
    questions = [
        q.model_copy(update={"evidence": check_evidence("open_questions", i, q.evidence)})
        for i, q in enumerate(summary.open_questions)
    ]
    actions = []
    for i, a in enumerate(summary.action_items):
        owner = a.owner
        if owner is not None and not _named(owner, known):
            warnings.append(f"action_items[{i}]: owner {owner!r} is not named in the transcript, removed")
            owner = None
        actions.append(a.model_copy(update={"owner": owner, "evidence": check_evidence("action_items", i, a.evidence)}))
    grounded = summary.model_copy(update={"decisions": decisions, "action_items": actions, "open_questions": questions})
    return grounded, warnings
