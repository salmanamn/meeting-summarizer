"""The evaluation's own data (D26): every scripted answer must be supported by the lines it points at, so a typo in
a keyword fails here instead of showing up as a model's miss."""

import json
from pathlib import Path

import pytest

from meeting.evaluate import KINDS, matches
from meeting.settings import load
from meeting.summarize import split
from meeting.transcript import Segment, Transcript

ROOT = Path(__file__).resolve().parents[2]
MEETINGS = sorted((ROOT / "eval" / "meetings").glob("*.json"))
SETS = json.loads((ROOT / "eval" / "sets.json").read_text())


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", MEETINGS, ids=lambda p: p.stem)
def test_answers_point_at_lines_that_support_them(path):
    m = read(path)
    assert m["id"] == path.stem
    assert set(m["answers"]) == {*KINDS, "forbidden"}
    for speaker, _ in m["lines"]:
        assert speaker in m["speakers"]
    for kind in KINDS:
        for ref in m["answers"][kind]:
            assert ref["lines"] and all(1 <= n <= len(m["lines"]) for n in ref["lines"]), ref
            text = " ".join(m["lines"][n - 1][1] for n in ref["lines"])
            assert matches(ref, text), f"{kind} {ref['keywords']} not in lines {ref['lines']}"
            if kind == "action_items" and ref.get("owner"):
                assert ref["owner"] in m["speakers"], ref
                assert ref["owner"] in text, f"{ref['owner']} is not named in lines {ref['lines']} (D6)"
            if ref.get("due"):
                assert matches({"keywords": [[ref["due"]]]}, text), ref
            if ref.get("source"):
                assert ref["source"] in [a["name"] for a in m.get("attachments", [])], ref


def test_the_sets_name_existing_meetings_and_do_not_overlap():
    scripted = {p.stem for p in MEETINGS}
    tuning, holdout = set(SETS["tuning"]), set(SETS["holdout"])
    assert not tuning & holdout
    for entry in tuning | holdout:
        assert entry.startswith("ami:") or entry in scripted, entry
    assert scripted == {e for e in tuning | holdout if not e.startswith("ami:")}


def test_the_long_meeting_is_split_with_the_default_part_size():
    """M05 exists to exercise the split and merge (D24): with one segment per line it must already need two parts."""
    m = read(ROOT / "eval" / "meetings" / "M05.json")
    t = Transcript(
        segments=[Segment(i * 5.0, i * 5.0 + 4, text) for i, (_, text) in enumerate(m["lines"])],
        language="en",
        audio_seconds=len(m["lines"]) * 5.0,
        seconds=1,
        engine="script",
    )
    assert len(split(t, load({}).part_max_chars)) >= 2
