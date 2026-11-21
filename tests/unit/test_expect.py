import pytest

from meeting.expect import check, normalize, wer
from meeting.summary import MeetingSummary

EXPECT = {
    "decisions": 2,
    "open_questions": 1,
    "action_items": [{"owner": "Omar", "keywords": ["number"]}, {"owner": "Lina", "keywords": ["icon"]}],
}


def summary(decisions=2, questions=1, actions=(("Omar", "Send the numbers"), ("Lina", "Approve the icons"))):
    return MeetingSummary.model_validate(
        {
            "title": "t",
            "overview": "o",
            "decisions": [{"text": f"d{i}", "evidence": None} for i in range(decisions)],
            "action_items": [{"task": t, "owner": o, "due": None, "evidence": None} for o, t in actions],
            "open_questions": [{"question": f"q{i}", "evidence": None} for i in range(questions)],
        }
    )


def test_normalize_and_wer():
    assert normalize("Let's meet on the 15th, OK?") == ["let's", "meet", "on", "the", "15th", "ok"]
    assert normalize("Don" + chr(0x2019) + "t") == ["don't"]
    assert wer("We release on Friday.", "we release on friday") == 0.0
    assert wer("we release on friday", "we released on friday") == pytest.approx(0.25)
    assert wer("", "") == 0.0


def test_everything_found():
    checks = check(summary(), EXPECT, transcript_wer=0.04)
    assert all(c.passed for c in checks), [c.label for c in checks if not c.passed]
    assert checks[0].label == "transcript WER 4.0% <= 15%"


def test_one_more_or_one_fewer_is_tolerated_but_not_two():
    assert all(c.passed for c in check(summary(decisions=3, questions=0), EXPECT))
    assert not check(summary(decisions=4), EXPECT)[0].passed


def test_a_wrong_owner_or_task_fails():
    labels = [
        c.label
        for c in check(summary(actions=(("Omar", "Send the numbers"), ("Sara", "Approve icons"))), EXPECT)
        if not c.passed
    ]
    assert labels == ["action for Lina (icon) found"]
    labels = [
        c.label
        for c in check(summary(actions=(("Omar", "Book a room"), ("Lina", "Approve icons"))), EXPECT)
        if not c.passed
    ]
    assert labels == ["action for Omar (number) found"]


def test_too_many_actions_fail():
    many = (("Omar", "numbers"), ("Lina", "icons"), ("Omar", "a"), ("Lina", "b"))
    assert [c.label for c in check(summary(actions=many), EXPECT) if not c.passed] == [
        "action_items: 4 found, 2 in the script (at most 3)"
    ]


def test_a_meeting_with_nothing_decided_must_produce_nothing():
    nothing = {"decisions": 0, "open_questions": 1, "action_items": []}
    assert all(c.passed for c in check(summary(decisions=0, actions=()), nothing))
    failed = [c.label for c in check(summary(decisions=1, actions=(("Omar", "x"),)), nothing) if not c.passed]
    assert failed == [
        "decisions: 1 found, 0 in the script (must be 0)",
        "action_items: 1 found, 0 in the script (must be 0)",
    ]


def test_high_wer_fails():
    assert not check(summary(), EXPECT, transcript_wer=0.2)[0].passed


def test_an_action_without_owner_must_stay_without_owner():
    expect = {"decisions": 0, "open_questions": 0, "action_items": [{"owner": None, "keywords": ["notes"]}]}
    ok = check(summary(decisions=0, questions=0, actions=((None, "Update the release notes"),)), expect)
    assert all(c.passed for c in ok)
    guessed = check(summary(decisions=0, questions=0, actions=(("Sara", "Update the release notes"),)), expect)
    assert [c.label for c in guessed if not c.passed] == ["action without an owner (notes) found"]
