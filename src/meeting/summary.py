"""The summary contract (D4): what the model must return, and the checks applied after it returns.

`summary_schema(stamps, refs)` is sent with the request (`response_format: json_schema`, strict). It is built per
call: every `evidence` field may only be one of the transcript's segment times, or null (D14), so a model cannot cite
a quote or a time that does not exist; with attachments, every item also gets a `source` that may only be one of
their block references, or null (D23). It stays inside the subset that Azure OpenAI's strict mode accepts: every
object lists all its properties as required and sets `additionalProperties: false`, optional values are
`["string", "null"]` or `anyOf` with null, `enum` for the times and references, and no length keywords. Lengths and
counts are enforced afterwards by the Pydantic models, and `ground()` checks the answer against the transcript
again: every evidence time must fall inside a segment, every owner must be a name that was actually said, every
`due` must be words the meeting used (D25), and a decision that only repeats an action item is dropped (D25).
"""

import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from meeting.transcript import Transcript, parse_stamp
from meeting.words import contains_phrase, covers, deadline_in

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]
Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
SAME_ITEM = 0.6  # share of an action item's content words in a decision with the same time: the same item (D28)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Decision(_Strict):
    text: Text
    evidence: str | None  # mm:ss of the segment where it was decided
    source: str | None = None  # an attachment block it refers to (D23); not in the schema without attachments


class ActionItem(_Strict):
    task: Text
    owner: Text | None  # a person named in the meeting; None when nobody was named (D6)
    due: Text | None  # as said ("Friday", "end of March"); never a date the model worked out (D25)
    evidence: str | None
    source: str | None = None


class OpenQuestion(_Strict):
    question: Text
    evidence: str | None
    source: str | None = None


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


def _one_of(values: list[str]) -> dict:
    return {"anyOf": [{"type": "string", "enum": list(dict.fromkeys(values))}, {"type": "null"}]}


def summary_schema(stamps: list[str], refs: list[str] | None = None) -> dict:
    """The schema for one call: `stamps` are the segment times (mm:ss) evidence may take; `refs` the attachment
    blocks a `source` may name (no `source` field at all without attachments)."""
    if not stamps:
        raise ValueError("a summary schema needs at least one segment time")
    evidence = _one_of(stamps)
    extra = {"source": _one_of(refs)} if refs else {}
    # Order matters for a model that writes left to right: the overview first, then the lists it summarises.
    return _object(
        {
            "title": _STRING,
            "overview": _STRING,
            "decisions": {"type": "array", "items": _object({"text": _STRING, "evidence": evidence, **extra})},
            "action_items": {
                "type": "array",
                "items": _object(
                    {"task": _STRING, "owner": _NULLABLE, "due": _NULLABLE, "evidence": evidence, **extra}
                ),
            },
            "open_questions": {
                "type": "array",
                "items": _object({"question": _STRING, "evidence": evidence, **extra}),
            },
        }
    )


def _named(name: str, text: str) -> bool:
    """The name, or every word of it, occurs as a whole word in the text (case ignored)."""
    words = re.findall(r"\w+", name.casefold())
    return bool(words) and all(re.search(rf"\b{re.escape(w)}\b", text) for w in words)


def ground(
    summary: MeetingSummary,
    transcript: Transcript,
    attendees: tuple[str, ...] = (),
    refs: tuple[str, ...] = (),
) -> tuple[MeetingSummary, list[str]]:
    """Check the summary against the transcript. Returns a corrected copy and one warning per correction:
    - evidence outside every segment becomes None;
    - an owner who is neither named in the transcript nor an attendee becomes None;
    - a `due` that is not words of the transcript, in that order, becomes None ("Wednesday" stays; "Wednesday
      Next, the 15th of March (00:27 ...)" goes);
    - a `source` that is not one of the attachments' blocks becomes None;
    - a decision with the same evidence time as an action item and mostly the same words is removed: it is the
      action item said again ("I will update the release notes" is a task, not a decision)."""
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

    def check_source(kind: str, index: int, source: str | None) -> str | None:
        if source is not None and source not in refs:
            warnings.append(f"{kind}[{index}]: source {source!r} is not an attachment block, removed")
            return None
        return source

    actions = []
    for i, a in enumerate(summary.action_items):
        owner, due = a.owner, a.due
        if owner is not None and not _named(owner, known):
            warnings.append(f"action_items[{i}]: owner {owner!r} is not named in the transcript, removed")
            owner = None
        if due is not None and not contains_phrase(transcript.text, due):
            kept = deadline_in(transcript.text, due)  # the meeting's words inside the model's comment (D28)
            if kept:
                warnings.append(f"action_items[{i}]: due {due!r} cut to the meeting's words {kept!r}")
            else:
                warnings.append(f"action_items[{i}]: due {due!r} is not what the meeting said, removed")
            due = kept
        actions.append(
            a.model_copy(
                update={
                    "owner": owner,
                    "due": due,
                    "evidence": check_evidence("action_items", i, a.evidence),
                    "source": check_source("action_items", i, a.source),
                }
            )
        )
    decisions = []
    for i, d in enumerate(summary.decisions):
        d = d.model_copy(
            update={
                "evidence": check_evidence("decisions", i, d.evidence),
                "source": check_source("decisions", i, d.source),
            }
        )
        twin = next(
            (
                a
                for a in actions
                if d.evidence is not None and a.evidence == d.evidence and covers(a.task, d.text) >= SAME_ITEM
            ),
            None,
        )
        if twin is not None:
            warnings.append(f"decisions[{i}]: repeats the action item at {d.evidence}, removed")
            continue
        decisions.append(d)
    questions = [
        q.model_copy(
            update={
                "evidence": check_evidence("open_questions", i, q.evidence),
                "source": check_source("open_questions", i, q.source),
            }
        )
        for i, q in enumerate(summary.open_questions)
    ]
    grounded = summary.model_copy(update={"decisions": decisions, "action_items": actions, "open_questions": questions})
    return grounded, warnings
