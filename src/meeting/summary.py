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

from meeting.transcript import Transcript, parse_stamp, stamp
from meeting.words import contains_phrase, content_words, covers, deadline_in

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]
Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
SAME_ITEM = 0.6  # share of one item's content words in the other, same time: a decision repeating an action (D28)
ANCHOR_WORDS = 2  # content words a segment must share with an item to count as saying it (D29)
ANCHOR_SECONDS = 60  # how far from a cited line that doesn't say the item its evidence may move (D31)
# A "decision" whose own words say nothing was decided ("an idea, not decided", "postponed") is not one (D31).
NOT_DECIDED = re.compile(
    r"\b(not (yet )?(been )?(decided|settled|agreed|finali[sz]ed)|undecided|no decision|to be decided|postponed|"
    r"an idea|deferred until|left open)\b",
    re.IGNORECASE,
)
OWNER_WINDOW = 1  # segments before and after the evidence where the owner's name must be said (D29, D32)
ADDRESSED_BEFORE = 2  # segments before the evidence searched for "Name, ..." addressed to an attendee (D32)


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
    # Room for the merged parts of an hour (D29: 20 decisions per call made AMI's merged summaries invalid).
    decisions: list[Decision] = Field(max_length=60)
    action_items: list[ActionItem] = Field(max_length=90)
    open_questions: list[OpenQuestion] = Field(max_length=60)


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


def _addressed(segments, attendees: tuple[str, ...], task: str) -> str | None:
    """The attendee a sentence in these segments starts by addressing ("Hana, the figures ..."), when that sentence
    is about the task (ANCHOR_WORDS of its content words); the nearest (last) of several; else None."""
    found, wanted = None, content_words(task)
    for seg in segments:
        for sentence in re.split(r"(?<=[.?!])\s+", seg.text.strip()):
            for name in attendees:
                about = len(wanted & content_words(sentence)) >= ANCHOR_WORDS
                if about and re.match(rf"{re.escape(name)}\s*,", sentence, re.IGNORECASE):
                    found = name
    return found


def ground(
    summary: MeetingSummary,
    transcript: Transcript,
    attendees: tuple[str, ...] = (),
    refs: tuple[str, ...] = (),
) -> tuple[MeetingSummary, list[str]]:
    """Check the summary against the transcript. Returns a corrected copy and one warning per correction:
    - evidence goes to a segment that says the item (D29, D31): the cited segment stands when it shares at least
      ANCHOR_WORDS of the item's content words; otherwise the evidence moves to the segment within ANCHOR_SECONDS
      that shares the most (at least ANCHOR_WORDS); missing or impossible evidence gets the best segment of the
      whole meeting, or None when none shares enough;
    - a decision whose own text says it was not decided ("an idea, not decided", "postponed") is removed (D31);
    - an owner must be named within OWNER_WINDOW segments of the evidence (D29), or anywhere in the transcript or
      the attendee list when there is no evidence (D6);
    - a `due` that is not words of the transcript, in that order, is cut to the meeting's words in it, or removed
      ("Tuesday (no specific date provided)" -> "Tuesday", D28);
    - a `source` that is not one of the attachments' blocks becomes None;
    - a decision with the same evidence time as an action item, where either holds 60 % of the other's content
      words, is removed: it is the action item said again (D25, D28, D29)."""
    known = " ".join([transcript.text, *attendees]).casefold()
    segments = transcript.segments
    words = [content_words(seg.text) for seg in segments]
    warnings: list[str] = []

    def index_of(evidence: str | None) -> int | None:
        seconds = parse_stamp(evidence) if evidence else None
        if seconds is None:
            return None
        exact = [i for i, seg in enumerate(segments) if stamp(seg.start) == evidence]
        if exact:
            return exact[0]
        return next((i for i, seg in enumerate(segments) if seg.start - 1 <= seconds <= seg.end + 1), None)

    def anchor(kind: str, index: int, text: str, evidence: str | None) -> tuple[str | None, int | None]:
        item = content_words(text)
        cited = index_of(evidence)
        shared = [len(item & w) for w in words]
        if cited is None:
            near, t = list(range(len(segments))), None  # no usable time: the whole meeting
        else:  # around the cited line only, never an agenda read out minutes earlier (D31)
            t = segments[cited].start
            near = [i for i, seg in enumerate(segments) if abs(seg.start - t) <= ANCHOR_SECONDS]
        # The line that says the most of the item; among equals the one nearest the cited time (D32), so a line
        # that only mentions the topic ("the release date", "the new icons") gives way to the one that settles it.
        best = max(near, key=lambda i: (shared[i], -abs(segments[i].start - t) if t is not None else -i), default=None)
        if best is not None and shared[best] >= ANCHOR_WORDS and (cited is None or shared[best] > shared[cited]):
            moved = stamp(segments[best].start)
            if evidence is not None and moved != evidence:
                where = "not inside any segment" if cited is None else "a line that says less of it"
                warnings.append(f"{kind}[{index}]: evidence {evidence!r} ({where}) moved to {moved!r}")
            elif evidence is None:
                warnings.append(f"{kind}[{index}]: evidence missing, set to {moved!r}")
            return moved, best
        if evidence is not None and cited is None:
            warnings.append(f"{kind}[{index}]: evidence {evidence!r} is not inside any segment, removed")
            return None, None
        return evidence, cited

    def check_source(kind: str, index: int, source: str | None) -> str | None:
        if source is not None and source not in refs:
            warnings.append(f"{kind}[{index}]: source {source!r} is not an attachment block, removed")
            return None
        return source

    actions = []
    for i, a in enumerate(summary.action_items):
        # The owner's name and the deadline say where a task was given ("Lina, ... by Friday"): they count (D32).
        evidence, at = anchor("action_items", i, " ".join(filter(None, [a.task, a.owner, a.due])), a.evidence)
        owner, due = a.owner, a.due
        if owner is not None:
            if at is None:
                said = _named(owner, known)
            else:
                window = " ".join(seg.text for seg in segments[max(0, at - OWNER_WINDOW) : at + OWNER_WINDOW + 1])
                said = _named(owner, window.casefold())
            if not said:
                where = "in the transcript" if at is None else "where the task is said"
                warnings.append(f"action_items[{i}]: owner {owner!r} is not named {where}, removed")
                owner = None
        if owner is None and at is not None:  # the attendee addressed just before ("Hana, the figures ...", D32)
            addressed = _addressed(segments[max(0, at - ADDRESSED_BEFORE) : at + 1], attendees, a.task)
            if addressed is not None:
                warnings.append(f"action_items[{i}]: owner set to {addressed!r}, addressed where the task is given")
                owner = addressed
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
                    "evidence": evidence,
                    "source": check_source("action_items", i, a.source),
                }
            )
        )
    decisions = []
    for i, d in enumerate(summary.decisions):
        if NOT_DECIDED.search(d.text):
            warnings.append(f"decisions[{i}]: says it was not decided, removed")
            continue
        evidence, _ = anchor("decisions", i, d.text, d.evidence)
        d = d.model_copy(update={"evidence": evidence, "source": check_source("decisions", i, d.source)})
        twin = next(
            (
                a
                for a in actions
                if d.evidence is not None
                and a.evidence == d.evidence
                and max(covers(a.task, d.text), covers(d.text, a.task)) >= SAME_ITEM
            ),
            None,
        )
        if twin is not None:
            warnings.append(f"decisions[{i}]: repeats the action item at {d.evidence}, removed")
            continue
        decisions.append(d)
    questions = []
    for i, q in enumerate(summary.open_questions):
        evidence, _ = anchor("open_questions", i, q.question, q.evidence)
        questions.append(
            q.model_copy(update={"evidence": evidence, "source": check_source("open_questions", i, q.source)})
        )
    grounded = summary.model_copy(update={"decisions": decisions, "action_items": actions, "open_questions": questions})
    return grounded, warnings
