"""The transcript: what the recording says, as timed segments. Every transcriber (faster-whisper locally, Azure AI
Speech batch transcription later) produces this one shape, and the summary only ever sees this shape (D2, D3)."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


def stamp(seconds: float) -> str:
    """mm:ss, or h:mm:ss from one hour on: the form the summary cites as evidence (D4)."""
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def parse_stamp(text: str) -> int | None:
    """Seconds for 'mm:ss' or 'h:mm:ss'; None for anything else."""
    parts = text.strip().split(":")
    if len(parts) not in (2, 3) or not all(p.isdigit() for p in parts):
        return None
    numbers = [int(p) for p in parts]
    if any(n >= 60 for n in numbers[1:]):
        return None
    seconds = 0
    for n in numbers:
        seconds = seconds * 60 + n
    return seconds


@dataclass(frozen=True)
class Segment:
    start: float  # seconds from the start of the recording
    end: float
    text: str
    speaker: str | None = None  # a diarization label ("Guest-1"), never a name; None from Whisper (D6)


@dataclass(frozen=True)
class Transcript:
    segments: list[Segment]
    language: str
    audio_seconds: float
    seconds: float  # wall time of the transcription
    engine: str  # which transcriber and model made it, e.g. "faster-whisper stt-small"
    warnings: list[str] = field(default_factory=list)

    @property
    def rtf(self) -> float:
        """Real-time factor: processing time / audio time (below 1 is faster than the recording)."""
        return self.seconds / self.audio_seconds if self.audio_seconds else 0.0

    @property
    def text(self) -> str:
        return " ".join(s.text for s in self.segments).strip()

    def timestamped(self) -> str:
        """One line per segment, '[mm:ss] text' (with '[mm:ss] Guest-1: text' when speakers are known)."""
        lines = []
        for s in self.segments:
            who = f"{s.speaker}: " if s.speaker else ""
            lines.append(f"[{stamp(s.start)}] {who}{s.text}")
        return "\n".join(lines)

    def covers(self, seconds: float, slack: float = 1.0) -> bool:
        """True when a moment falls inside a segment (with a little slack at both ends)."""
        return any(s.start - slack <= seconds <= s.end + slack for s in self.segments)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n"

    @classmethod
    def from_json(cls, text: str) -> "Transcript":
        data = json.loads(text)
        data["segments"] = [Segment(**s) for s in data["segments"]]
        return cls(**data)

    @classmethod
    def read(cls, path: Path) -> "Transcript":
        return cls.from_json(path.read_text(encoding="utf-8"))
