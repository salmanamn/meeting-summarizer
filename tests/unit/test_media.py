"""File types from content, and the recording's duration (D16)."""

import pytest
from fakes import wav_bytes

from meeting.media import Unreadable, attachment_kind, audio_kind, duration_seconds


@pytest.mark.parametrize(
    ("head", "kind"),
    [
        (wav_bytes(0.1)[:64], "wav"),
        (b"ID3\x04\x00" + b"\0" * 20, "mp3"),
        (b"\xff\xfb\x90\x64" + b"\0" * 20, "mp3"),
        (b"\x00\x00\x00\x20ftypM4A " + b"\0" * 10, "m4a"),
        (b"OggS\x00\x02" + b"\0" * 20, "ogg"),
        (b"fLaC\x00\x00" + b"\0" * 20, "flac"),
        (b"\x1a\x45\xdf\xa3\x9f" + b"\0" * 20, "webm"),
        (b"RIFF\x00\x00\x00\x00AVI " + b"\0" * 20, None),
        (b"%PDF-1.7", None),
        (b"hello, this is text", None),
        (b"", None),
    ],
)
def test_audio_kind(head, kind):
    assert audio_kind(head) == kind


def test_attachment_kind():
    assert attachment_kind(b"%PDF-1.7\n", "agenda.pdf") == "pdf"
    assert attachment_kind(b"%PDF-1.7\n", "agenda.docx") == "pdf"  # the content wins over the name
    assert attachment_kind(b"PK\x03\x04", "notes.docx") == "docx"
    assert attachment_kind(b"PK\x03\x04", "notes.zip") is None
    assert attachment_kind(b"{\\rtf1", "notes.docx") is None


def test_duration_from_the_container(tmp_path):
    path = tmp_path / "a.wav"
    path.write_bytes(wav_bytes(2.5))
    assert duration_seconds(path) == pytest.approx(2.5)


@pytest.mark.parametrize("data", [b"hello world", b"RIFF\x00\x00\x00\x00WAVEgarbage" * 4])
def test_unreadable_files(tmp_path, data):
    path = tmp_path / "x.wav"
    path.write_bytes(data)
    with pytest.raises(Unreadable):
        duration_seconds(path)
