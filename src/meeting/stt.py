"""Speech to text on the laptop: faster-whisper (Whisper on CTranslate2), CPU (D2, D13).

A meeting is long-form audio. The default `batched` mode cuts the recording at pauses (voice-activity detection)
into pieces of at most 30 seconds and transcribes each piece on its own, as plain text: nothing lets Whisper skip
ahead, which `sequential` (Whisper's own 30-second sliding window, with timestamp tokens) did on 3 of 5 synthetic
meetings (D13). The times come from word alignment instead (cross-attention, after decoding, so it cannot change
the words), and the words are regrouped into sentences: those are the segments the summary cites as evidence.
"""

import json
import time
from pathlib import Path
from typing import Protocol

from meeting.settings import Settings
from meeting.transcript import Segment, Transcript

REQUIRED_FILES = ("model.bin", "config.json", "tokenizer.json")
SENTENCE_END = (".", "?", "!")


def sentences(words) -> list[Segment]:
    """Regroup timed words (faster-whisper `Word`: start, end, word with its leading space) into sentences."""
    out, current = [], []
    for word in words:
        current.append(word)
        if word.word.strip().endswith(SENTENCE_END):
            out.append(current)
            current = []
    if current:
        out.append(current)
    segments = []
    for group in out:
        text = "".join(w.word for w in group).strip()
        if text:
            segments.append(
                Segment(start=round(float(group[0].start), 2), end=round(float(group[-1].end), 2), text=text)
            )
    return segments


class Transcriber(Protocol):
    """Audio file in, transcript out: faster-whisper here. Azure AI Speech batch transcription is the other kind
    (`meeting.speech`, `remote = True`): it reads the blob itself, so the job hands it a URL instead (D3, D44)."""

    def transcribe(self, audio: Path, *, names: tuple[str, ...] = ()) -> Transcript: ...


class WhisperTranscriber:
    def __init__(
        self,
        model_dir: Path,
        *,
        language: str = "en",
        compute_type: str = "int8",
        threads: int = 4,
        beam_size: int = 5,
        mode: str = "batched",
        batch_size: int = 4,
    ) -> None:
        from faster_whisper import BatchedInferencePipeline, WhisperModel  # only this transcriber needs CTranslate2

        if mode not in ("batched", "sequential"):
            raise ValueError(f"STT_MODE must be batched or sequential, not {mode!r}")
        # Without this check faster-whisper would try to download what is missing from the Hugging Face Hub.
        missing = [name for name in REQUIRED_FILES if not (model_dir / name).is_file()]
        if missing:
            raise FileNotFoundError(f"{model_dir}: missing {', '.join(missing)} (run scripts/fetch_models.py)")
        if mode == "batched" and "alignment_heads" not in json.loads((model_dir / "config.json").read_text()):
            raise ValueError(f"{model_dir}: config.json has no alignment_heads, needed for word times (STT_MODE)")
        self.name = f"faster-whisper {model_dir.name} {mode}"
        self.language = language or None  # None: Whisper detects the language from the first 30 seconds
        self.beam_size = beam_size
        self.mode = mode
        self.batch_size = batch_size
        self._model = WhisperModel(str(model_dir), device="cpu", compute_type=compute_type, cpu_threads=threads)
        self._batched = BatchedInferencePipeline(self._model)

    @classmethod
    def from_settings(cls, settings: Settings) -> "WhisperTranscriber":
        return cls(
            settings.stt_model_dir,
            language=settings.stt_language,
            compute_type=settings.stt_compute_type,
            threads=settings.stt_threads,
            beam_size=settings.stt_beam_size,
            mode=settings.stt_mode,
            batch_size=settings.stt_batch_size,
        )

    def transcribe(self, audio: Path, *, names: tuple[str, ...] = ()) -> Transcript:
        """`names`: the attendees, passed to Whisper as hotwords on every window, so that a name is spelled the
        way the invite spells it ("Lina", not "Lena"); the summary's owners depend on it (D6)."""
        started = time.perf_counter()
        options = {
            "language": self.language,
            "task": "transcribe",
            "beam_size": self.beam_size,
            "condition_on_previous_text": False,  # one misheard window must not repeat through the rest
            "vad_filter": True,  # silence is removed first: Whisper invents text for non-speech
            "hotwords": ", ".join(names) or None,
        }
        if self.mode == "batched":
            pieces, info = self._batched.transcribe(
                str(audio), batch_size=self.batch_size, without_timestamps=True, word_timestamps=True, **options
            )
            kept = sentences(word for piece in pieces for word in piece.words)  # the generator does the work here
        else:
            segments, info = self._model.transcribe(str(audio), without_timestamps=False, **options)
            kept = [Segment(start=round(s.start, 2), end=round(s.end, 2), text=s.text.strip()) for s in segments]
            kept = [s for s in kept if s.text]
        return Transcript(
            segments=kept,
            language=info.language,
            audio_seconds=round(info.duration, 2),
            seconds=round(time.perf_counter() - started, 2),
            engine=self.name,
        )
