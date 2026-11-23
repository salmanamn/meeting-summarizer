"""Configuration. Everything comes from environment variables, so the same code runs on the laptop, in the
Functions host and on Azure; the defaults are the laptop values (D8)."""

import os
from dataclasses import dataclass
from pathlib import Path

# The Cosmos DB emulator's well-known key (public, the same in every emulator). Only used when COSMOS_ENDPOINT is
# the emulator's default address: anywhere else an empty key means Entra ID (D8, D17).
COSMOS_EMULATOR_ENDPOINT = "http://localhost:8081"
COSMOS_EMULATOR_KEY = "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
MB = 1024 * 1024


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
    chat_reasoning_effort: (
        str  # none: a local model with thinking off (D33); empty: classic models; low...: reasoning models (Azure)
    )
    summary_max_tokens: int
    transcript_max_chars: int  # longer transcripts are refused before any model call (D4, D24)
    part_max_chars: int  # a longer transcript is summarised in parts of at most this, then merged (D24)
    attachment_context_chars: int  # attachment text given to every call, whole blocks, in order (D23)

    # Stores (M2). The recordings account: a connection string locally (Azurite), or only its blob service URI on
    # Azure, which means the app's managed identity (the same setting names the Functions host reads, D17).
    recordings_connection: str  # RecordingsStorage
    recordings_service_uri: str  # RecordingsStorage__blobServiceUri
    incoming_container: str
    transcripts_container: str
    cosmos_endpoint: str
    cosmos_key: str  # empty: Entra ID
    cosmos_database: str
    jobs_container: str

    # Limits, checked before any model runs (D16). Sizes in bytes.
    max_manifest_bytes: int
    max_recording_bytes: int
    max_attachment_bytes: int
    max_recording_seconds: int
    max_attachment_pages: int  # a PDF with more pages is refused (D22)
    job_max_attempts: int  # must equal host.json extensions.blobs.poisonBlobThreshold (a unit test checks)
    model_retry_base_seconds: int  # wait before a model error is retried: base, doubling per attempt (D21)
    model_retry_max_seconds: int  # ... up to this

    @property
    def stt_model_dir(self) -> Path:
        return self.models_dir / self.stt_model


def default_threads() -> int:
    """CPUs this process may use (respects container CPU pinning), capped: Whisper gains little beyond 8."""
    return max(1, min(len(os.sched_getaffinity(0)), 8))


def load(env: dict[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    cosmos_endpoint = env.get("COSMOS_ENDPOINT", COSMOS_EMULATOR_ENDPOINT)
    emulator = cosmos_endpoint.rstrip("/") == COSMOS_EMULATOR_ENDPOINT
    service_uri = env.get("RecordingsStorage__blobServiceUri", "")
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
        chat_model=env.get("CHAT_MODEL", "qwen3.5:4b"),
        chat_reasoning_effort=env.get("CHAT_REASONING_EFFORT", "none"),
        summary_max_tokens=int(env.get("SUMMARY_MAX_TOKENS", "3000")),
        transcript_max_chars=int(env.get("TRANSCRIPT_MAX_CHARS", "100000")),
        part_max_chars=int(env.get("PART_MAX_CHARS", "6000")),
        attachment_context_chars=int(env.get("ATTACHMENT_CONTEXT_CHARS", "4000")),
        recordings_connection="" if service_uri else env.get("RecordingsStorage", "UseDevelopmentStorage=true"),
        recordings_service_uri=service_uri,
        incoming_container=env.get("INCOMING_CONTAINER", "incoming"),
        transcripts_container=env.get("TRANSCRIPTS_CONTAINER", "transcripts"),
        cosmos_endpoint=cosmos_endpoint,
        cosmos_key=env.get("COSMOS_KEY", COSMOS_EMULATOR_KEY if emulator else ""),
        cosmos_database=env.get("COSMOS_DATABASE", "meetings"),
        jobs_container=env.get("COSMOS_JOBS_CONTAINER", "jobs"),
        max_manifest_bytes=int(env.get("MAX_MANIFEST_KB", "64")) * 1024,
        max_recording_bytes=int(env.get("MAX_RECORDING_MB", "300")) * MB,
        max_attachment_bytes=int(env.get("MAX_ATTACHMENT_MB", "20")) * MB,
        max_recording_seconds=int(env.get("MAX_RECORDING_MINUTES", "60")) * 60,
        max_attachment_pages=int(env.get("MAX_ATTACHMENT_PAGES", "50")),
        job_max_attempts=int(env.get("JOB_MAX_ATTEMPTS", "5")),
        model_retry_base_seconds=int(env.get("MODEL_RETRY_BASE_SECONDS", "30")),
        model_retry_max_seconds=int(env.get("MODEL_RETRY_MAX_SECONDS", "120")),
    )
