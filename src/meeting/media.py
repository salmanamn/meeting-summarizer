"""What a file is, from its bytes, not its name (D16): the first bytes of every upload are read before anything else
touches it, and the recording's duration is read from its container before speech to text starts."""

from pathlib import Path

HEAD_BYTES = 64  # enough for every signature below


def audio_kind(head: bytes) -> str | None:
    """'wav', 'mp3', 'm4a', 'ogg', 'flac' or 'webm' from the first bytes of a file; None for anything else."""
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if head[:3] == b"ID3" or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0):
        return "mp3"  # an ID3 tag, or an MPEG audio frame header (11 sync bits)
    if head[4:8] == b"ftyp":
        return "m4a"  # MP4 family (also video MP4; the duration check below needs an audio stream)
    if head[:4] == b"OggS":
        return "ogg"
    if head[:4] == b"fLaC":
        return "flac"
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"  # Matroska / WebM
    return None


def attachment_kind(head: bytes, name: str) -> str | None:
    """'pdf' or 'docx'. A DOCX is a ZIP file, so the bytes can only say "ZIP": the name decides between DOCX and any
    other ZIP, and M3's converter refuses a ZIP that isn't a Word document."""
    if head[:5] == b"%PDF-":
        return "pdf"
    if head[:4] == b"PK\x03\x04" and name.lower().endswith(".docx"):
        return "docx"
    return None


class Unreadable(ValueError):
    """FFmpeg (through PyAV) cannot read the file as audio."""


def duration_seconds(path: Path) -> float:
    """The recording's length from its container (no decoding). Raises Unreadable for a file without audio."""
    import av  # only the job needs PyAV (the stt group, D10)

    try:
        with av.open(str(path), metadata_errors="ignore") as container:
            streams = container.streams.audio
            if not streams:
                raise Unreadable("no audio stream")
            if container.duration is not None:
                return container.duration / av.time_base
            stream = streams[0]
            if stream.duration is not None and stream.time_base is not None:
                return float(stream.duration * stream.time_base)
    except av.error.FFmpegError:
        raise Unreadable("not a readable media file") from None
    raise Unreadable("the file states no duration")
