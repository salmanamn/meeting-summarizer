from pathlib import Path

from meeting.settings import default_threads, load


def test_defaults_are_the_laptop_values():
    settings = load({})
    assert settings.stt_model_dir == Path("models/stt-small")
    assert settings.stt_language == "en"
    assert settings.stt_compute_type == "int8"
    assert settings.stt_threads == default_threads()
    assert 1 <= settings.stt_threads <= 8
    assert settings.openai_base_url == "http://127.0.0.1:11434/v1"
    assert settings.chat_model == "phi4-mini:3.8b"
    assert settings.chat_reasoning_effort == ""
    assert settings.summary_max_tokens == 1500
    assert settings.transcript_max_chars == 40000


def test_environment_overrides():
    settings = load(
        {
            "MODELS_DIR": "/models",
            "STT_MODEL": "stt-tiny",
            "STT_LANGUAGE": "",
            "STT_THREADS": "3",
            "OPENAI_BASE_URL": "https://example.openai.azure.com/openai/v1",
            "CHAT_MODEL": "gpt-5.4-mini",
            "CHAT_REASONING_EFFORT": "low",
            "SUMMARY_MAX_TOKENS": "4000",
            "TRANSCRIPT_MAX_CHARS": "100",
        }
    )
    assert settings.stt_model_dir == Path("/models/stt-tiny")
    assert settings.stt_language == ""  # empty: Whisper detects the language
    assert settings.stt_threads == 3
    assert settings.chat_model == "gpt-5.4-mini"
    assert settings.chat_reasoning_effort == "low"
    assert settings.summary_max_tokens == 4000
    assert settings.transcript_max_chars == 100


def test_store_defaults_are_the_emulators():
    settings = load({})
    assert settings.recordings_connection == "UseDevelopmentStorage=true"
    assert settings.recordings_service_uri == ""
    assert (settings.incoming_container, settings.transcripts_container) == ("incoming", "transcripts")
    assert settings.cosmos_endpoint == "http://localhost:8081"
    assert settings.cosmos_key.startswith("C2y6yDjf5")  # the emulator's published key, only for its address
    assert (settings.cosmos_database, settings.jobs_container) == ("meetings", "jobs")
    assert settings.max_manifest_bytes == 64 * 1024
    assert settings.max_recording_bytes == 300 * 1024 * 1024
    assert settings.max_attachment_bytes == 20 * 1024 * 1024
    assert settings.max_recording_seconds == 3600
    assert settings.job_max_attempts == 5
    assert (settings.model_retry_base_seconds, settings.model_retry_max_seconds) == (30, 120)


def test_azure_values_mean_identity_not_keys():
    settings = load(
        {
            "RecordingsStorage__blobServiceUri": "https://strecordings.blob.core.windows.net",
            "RecordingsStorage": "UseDevelopmentStorage=true",  # ignored once the service URI is set
            "COSMOS_ENDPOINT": "https://cosmos-meetings.documents.azure.com:443/",
        }
    )
    assert settings.recordings_connection == ""
    assert settings.recordings_service_uri == "https://strecordings.blob.core.windows.net"
    assert settings.cosmos_key == ""  # no emulator key anywhere but the emulator's address
