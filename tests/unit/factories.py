"""Test data builders (imported by conftest.py and the tests; pytest puts tests/unit on the import path)."""

from meeting.transcript import Segment, Transcript


def make_transcript(*lines: tuple[float, float, str]) -> Transcript:
    return Transcript(
        segments=[Segment(start=s, end=e, text=t) for s, e, t in lines],
        language="en",
        audio_seconds=lines[-1][1] if lines else 0.0,
        seconds=1.0,
        engine="test",
    )
