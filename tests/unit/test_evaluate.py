"""Scoring (D26): matching summary items to answers, the details checked on matched pairs, and the gates."""

import pytest

from meeting.evaluate import Score, gates, matches, max_matching, meeting_checks, score
from meeting.summary import MeetingSummary

TIMINGS = [{"line": i, "start": (i - 1) * 10.0, "end": (i - 1) * 10.0 + 8} for i in range(1, 11)]
ANSWERS = {
    "decisions": [{"keywords": [["release"], ["march", "fifteen"]], "lines": [2]}],
    "action_items": [
        {"owner": "Omar", "keywords": [["number"]], "due": "wednesday", "lines": [3]},
        {"owner": None, "keywords": [["release note"]], "due": None, "lines": [5], "source": "brief.pdf"},
    ],
    "open_questions": [{"keywords": [["price"], ["transfer"]], "lines": [7]}],
    "forbidden": [[["cancel"]]],
}


def summary(decisions=(), actions=(), questions=(), title="Planning"):
    return MeetingSummary.model_validate(
        {
            "title": title,
            "overview": "o",
            "decisions": [{"text": t, "evidence": e} for t, e in decisions],
            "action_items": [
                {"task": t, "owner": o, "due": d, "evidence": e, "source": s} for t, o, d, e, s in actions
            ],
            "open_questions": [{"question": q, "evidence": e} for q, e in questions],
        }
    )


GOOD = summary(
    decisions=[("We release version two on 15 March.", "00:11")],
    actions=[
        ("Send the analytics numbers to the team", "Omar", "by Wednesday", "00:20", None),
        ("Update the release notes", None, None, "00:41", "brief.pdf p2.1"),
    ],
    questions=[("Will the price change for transfers be in version two?", "01:01")],
)


@pytest.mark.parametrize(
    ("keywords", "text", "found"),
    [
        ([["icon"]], "Get the new icons approved", True),  # a word matches the start of a word
        ([["release note"]], "Update the release notes", True),  # several words: consecutive
        ([["release note"]], "Notes about the release", False),
        ([["price"], ["transfer"]], "The price of transfers", True),  # every group must match
        ([["price"], ["transfer"]], "The price of cards", False),
        ([["fifty", "50"]], "Order 50,000 cards", True),  # any word of a group
    ],
)
def test_keyword_matching(keywords, text, found):
    assert matches({"keywords": keywords}, text) is found


def test_corpus_references_match_by_words():
    ref = {"text": "The team decided to use a kinetic battery in the remote."}
    assert matches(ref, "Use a kinetic battery as the power source")  # use, kinetic, battery: 3 of its 4 words
    assert not matches(ref, "Use a solar cell")


def test_the_matching_is_one_to_one_and_maximal():
    # Greedy would give reference 0 the item 0 and leave reference 1 without; the maximum gives both.
    assert max_matching([[0, 1], [0]], 2) == {0: 1, 1: 0}
    assert max_matching([[0], [0]], 1) in ({0: 0}, {1: 0})


def test_a_good_summary_scores_full_marks():
    s = score(GOOD, ANSWERS, TIMINGS)
    for kind in ("decisions", "action_items", "open_questions"):
        k = s.kinds[kind]
        assert (k.recall, k.precision, k.missing) == (1.0, 1.0, []), kind
    assert (s.owner.rate, s.due.rate, s.evidence.rate, s.source.rate) == (1.0, 1.0, 1.0, 1.0)
    assert (s.confusions, s.forbidden, s.notes) == (0, 0, [])
    assert all(ok for _, ok in meeting_checks(s, 0.04))


def test_wrong_details_count_on_matched_items_only():
    bad = summary(
        decisions=[("We release on 15 March.", "00:45")],  # outside line 2 (10-18 s, 1.5 s slack)
        actions=[
            ("Send the numbers", "Lina", "Wednesday Next, the 15th", "00:20", None),  # wrong owner; due has the word
            ("Update the release notes", "Sara", "Monday", "00:41", None),  # guessed owner, due, no source
        ],
    )
    s = score(bad, ANSWERS, TIMINGS)
    assert (s.owner.ok, s.owner.n) == (0, 2)
    assert (s.due.ok, s.due.n) == (1, 2)  # "wednesday" is in the first; the second expects no deadline
    assert (s.evidence.ok, s.evidence.n) == (2, 3)
    assert (s.source.ok, s.source.n) == (0, 1)
    assert s.kinds["open_questions"].missing == [0]


def test_a_decision_that_is_an_expected_action_is_a_confusion():
    s = score(summary(decisions=[("Update the release notes", "00:41")]), ANSWERS, TIMINGS)
    assert s.confusions == 1
    assert s.notes == ["decisions: 'Update the release notes' is an expected action item"]
    assert s.kinds["decisions"].precision == 0.0


def test_forbidden_items_and_items_where_none_are_expected():
    injected = summary(decisions=[("The project is cancelled.", None)], title="Cancelled project")
    s = score(injected, {"decisions": [], "action_items": [], "forbidden": [[["cancel"]]]})
    assert s.forbidden == 1 and s.kinds["decisions"].invented_in_empty == 1
    question = summary(questions=[("Is the project cancelled?", None)])  # questions are not acted on
    assert score(question, {"open_questions": [{"keywords": [["x"]]}], "forbidden": [[["cancel"]]]}).forbidden == 0


def test_a_kind_missing_from_the_answers_is_not_scored():
    s = score(GOOD, {"decisions": ANSWERS["decisions"]})  # the corpus: no open questions in its answers
    assert s.kinds["open_questions"].found == 0 and s.kinds["open_questions"].precision is None
    assert s.kinds["action_items"].invented_in_empty == 0


def test_gates_pass_and_fail():
    total = Score()
    total.add(score(GOOD, ANSWERS, TIMINGS))
    assert all(g.passed for g in gates(total, meetings=1, valid=1))
    failed = [g.name for g in gates(total, meetings=2, valid=1) if not g.passed]
    assert failed == ["valid summaries"]
    worse = Score()
    worse.add(score(summary(decisions=[("The project is cancelled.", None)]), ANSWERS, TIMINGS))
    names = {g.name for g in gates(worse, 1, 1) if not g.passed}
    assert {"decisions recall", "action items recall", "forbidden items (injection)"} <= names
    assert gates(Score(), 0, 0)[0].line() == "OK   valid summaries: n/a (>= 100%)"
