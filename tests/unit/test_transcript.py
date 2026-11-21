import pytest
from factories import make_transcript

from meeting.transcript import Segment, Transcript, parse_stamp, stamp


@pytest.mark.parametrize(
    ("seconds", "text"),
    [(0, "00:00"), (7.9, "00:07"), (75, "01:15"), (3599, "59:59"), (3600, "1:00:00"), (3725.5, "1:02:05")],
)
def test_stamp(seconds, text):
    assert stamp(seconds) == text


@pytest.mark.parametrize(
    ("text", "seconds"),
    [
        ("00:00", 0),
        ("01:15", 75),
        (" 1:02:05 ", 3725),
        ("75:00", 4500),
        ("1:75", None),
        ("1:00:60", None),
        ("12", None),
        ("aa:bb", None),
        ("", None),
        ("1:2:3:4", None),
    ],
)
def test_parse_stamp(text, seconds):
    assert parse_stamp(text) == seconds


def test_timestamped_lines_and_text(transcript):
    lines = transcript.timestamped().splitlines()
    assert lines[0] == "[00:00] Good morning. Omar, please send the numbers by Wednesday."
    assert lines[3].startswith("[01:15] Who presents")
    assert transcript.text.startswith("Good morning. Omar") and transcript.text.endswith("come back to that.")


def test_speaker_labels_are_shown_when_known():
    t = Transcript(
        segments=[Segment(0, 2, "Hello.", speaker="Guest-1")], language="en", audio_seconds=2, seconds=1, engine="x"
    )
    assert t.timestamped() == "[00:00] Guest-1: Hello."


def test_covers_allows_one_second_of_slack(transcript):
    assert transcript.covers(0) and transcript.covers(6.5) and transcript.covers(12.9)
    assert not transcript.covers(40)  # between segments 3 and 4
    assert not transcript.covers(81.5)


def test_json_round_trip(transcript, tmp_path):
    path = tmp_path / "t.json"
    path.write_text(transcript.to_json(), encoding="utf-8")
    assert Transcript.read(path) == transcript


def test_rtf():
    assert make_transcript((0, 10, "a")).rtf == pytest.approx(0.1)
    assert Transcript(segments=[], language="en", audio_seconds=0, seconds=1, engine="x").rtf == 0.0
