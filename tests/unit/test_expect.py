import pytest

from meeting.expect import normalize, wer


def test_normalize_and_wer():
    assert normalize("Let's meet on the 15th, OK?") == ["let's", "meet", "on", "the", "15th", "ok"]
    assert normalize("Don" + chr(0x2019) + "t") == ["don't"]
    assert wer("We release on Friday.", "we release on friday") == 0.0
    assert wer("we release on friday", "we released on friday") == pytest.approx(0.25)
    assert wer("", "") == 0.0
    assert wer("", "words") == 1.0
