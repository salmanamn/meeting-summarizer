"""Configuration. Everything comes from environment variables, so the same code runs on the laptop, in the
Functions host and on Azure; the defaults are the laptop values (D8)."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    models_dir: Path

    stt_model: str  # directory name under models_dir
    stt_language: str  # Whisper language code; empty = let Whisper detect it (D2)
    stt_compute_type: str
    stt_threads: int
    stt_beam_size: int
    stt_mode: str  # batched (default: pieces cut at pauses) or sequential (Whisper's sliding window), D13
    stt_batch_size: int

    openai_base_url: str  # any OpenAI-compatible endpoint: Ollama locally, Azure OpenAI later (D5)
    openai_api_key: str
    openai_timeout: float
    chat_model: str
    chat_reasoning_effort: str  # empty for classic chat models; set for reasoning models (Azure)
    summary_max_tokens: int
    transcript_max_chars: int  # longer transcripts are refused before any model call (D4)

    @property
    def stt_model_dir(self) -> Path:
        return self.models_dir / self.stt_model


def default_threads() -> int:
    """CPUs this process may use (respects container CPU pinning), capped: Whisper gains little beyond 8."""
    return max(1, min(len(os.sched_getaffinity(0)), 8))


def load(env: dict[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    return Settings(
        models_dir=Path(env.get("MODELS_DIR", "models")),
        stt_model=env.get("STT_MODEL", "stt-small"),
        stt_language=env.get("STT_LANGUAGE", "en"),
        stt_compute_type=env.get("STT_COMPUTE_TYPE", "int8"),
        stt_threads=int(env.get("STT_THREADS", "0")) or default_threads(),
        stt_beam_size=int(env.get("STT_BEAM_SIZE", "5")),
        stt_mode=env.get("STT_MODE", "batched"),
        stt_batch_size=int(env.get("STT_BATCH_SIZE", "4")),
        openai_base_url=env.get("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1"),
        openai_api_key=env.get("OPENAI_API_KEY", "ollama"),  # Ollama ignores the key; the SDK requires one
        openai_timeout=float(env.get("OPENAI_TIMEOUT_SECONDS", "300")),
        chat_model=env.get("CHAT_MODEL", "phi4-mini:3.8b"),
        chat_reasoning_effort=env.get("CHAT_REASONING_EFFORT", ""),
        summary_max_tokens=int(env.get("SUMMARY_MAX_TOKENS", "1500")),
        transcript_max_chars=int(env.get("TRANSCRIPT_MAX_CHARS", "40000")),
    )
