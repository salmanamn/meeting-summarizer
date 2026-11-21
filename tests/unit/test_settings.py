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
