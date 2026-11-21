"""The M1 check for a scripted test meeting (D7): did the transcript come out close to the script, and did the
summary find what the script contains, without inventing more? A smoke test with loose limits, not the evaluation
(that comes with a larger set of meetings and scored matching in M3).

A meeting file (eval/meetings/*.json) carries the script and an `expect` block:
    {"decisions": 2, "open_questions": 1,
     "action_items": [{"owner": "Omar", "keywords": ["budget", "estimate"]}, {"owner": null, ...}]}
An owner of null means the script gives no way to tell from the words who took the task (D6, D14): the summary must
then leave the owner empty too; a guessed name, even the right one, is not grounded.
"""

import re
import unicodedata
from dataclasses import dataclass

from meeting.summary import MeetingSummary

MAX_WER = 0.15  # clean synthetic speech: a working transcriber stays well below this


def normalize(text: str) -> list[str]:
    """Words for scoring English: lower case, no punctuation, apostrophes kept inside words."""
    text = unicodedata.normalize("NFKC", text).casefold().replace("\u2019", "'")  # typographic apostrophe
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text)


def edit_distance(ref: list[str], hyp: list[str]) -> int:
    previous = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, start=1):
        current = [i]
        for j, h in enumerate(hyp, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (r != h)))
        previous = current
    return previous[-1]


def wer(reference: str, hypothesis: str) -> float:
    ref, hyp = normalize(reference), normalize(hypothesis)
    return edit_distance(ref, hyp) / len(ref) if ref else float(bool(hyp))


@dataclass(frozen=True)
class Check:
    label: str
    passed: bool


def check(summary: MeetingSummary, expect: dict, *, transcript_wer: float | None = None) -> list[Check]:
    checks = []
    if transcript_wer is not None:
        checks.append(Check(f"transcript WER {transcript_wer:.1%} <= {MAX_WER:.0%}", transcript_wer <= MAX_WER))

    for kind in ("decisions", "open_questions"):
        want, got = expect[kind], len(getattr(summary, kind))
        # Zero must be exactly zero (nothing invented); otherwise one more or one fewer is tolerated (wording varies).
        ok = got == 0 if want == 0 else abs(got - want) <= 1
        checks.append(Check(f"{kind}: {got} found, {want} in the script{'' if want else ' (must be 0)'}", ok))

    wanted = expect["action_items"]
    items = summary.action_items
    if not wanted:
        checks.append(Check(f"action_items: {len(items)} found, 0 in the script (must be 0)", not items))
    else:
        limit = len(wanted) + 1
        checks.append(
            Check(
                f"action_items: {len(items)} found, {len(wanted)} in the script (at most {limit})", len(items) <= limit
            )
        )
        for item in wanted:
            owner = (item["owner"] or "").casefold()
            match = any(
                (a.owner or "").casefold() == owner and any(k in a.task.casefold() for k in item["keywords"])
                for a in items
            )
            who = f"for {item['owner']}" if item["owner"] else "without an owner"
            checks.append(Check(f"action {who} ({' / '.join(item['keywords'])}) found", match))
    return checks
