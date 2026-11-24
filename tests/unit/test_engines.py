"""Which transcriber and which credentials (D44, D46): chosen by settings, the same code on the laptop and on Azure."""

import json
from pathlib import Path

import httpx
import pytest
from openai import OpenAI

import function_app
from meeting import llm
from meeting.llm import COGNITIVE_SCOPE, JsonModel
from meeting.settings import SettingsInvalid, load
from meeting.speech import SpeechTranscriber

SRC = Path(__file__).resolve().parents[2] / "src"
ENDPOINT = "https://spch-meeting-abcde.cognitiveservices.azure.com/"


def test_the_laptop_default_is_whisper_with_a_key():
    s = load({})
    assert (s.stt_engine, s.openai_auth, s.speech_endpoint) == ("whisper", "key", "")
    assert (s.speech_locale, s.speech_poll_seconds, s.speech_wait_seconds) == ("en-US", 15, 1200)


def test_the_stack_s_settings_select_speech():
    """envs/azure sets SPEECH_ENDPOINT and no STT_ENGINE: that alone means Speech (no Whisper model on Azure)."""
    s = load({"SPEECH_ENDPOINT": ENDPOINT, "SPEECH_REGION": "uaenorth", "OPENAI_AUTH": "entra"})
    assert (s.stt_engine, s.speech_region, s.openai_auth) == ("speech", "uaenorth", "entra")


def test_stt_engine_overrides_the_endpoint():
    assert load({"SPEECH_ENDPOINT": ENDPOINT, "STT_ENGINE": "whisper"}).stt_engine == "whisper"


@pytest.mark.parametrize(
    ("env", "match"),
    [
        ({"STT_ENGINE": "speech"}, "needs SPEECH_ENDPOINT"),
        ({"STT_ENGINE": "azure"}, "STT_ENGINE must be"),
        ({"OPENAI_AUTH": "managedidentity"}, "OPENAI_AUTH must be"),
        ({"SPEECH_POLL_SECONDS": "0"}, "SPEECH_POLL_SECONDS"),
        ({"SPEECH_POLL_SECONDS": "60", "SPEECH_WAIT_SECONDS": "30"}, "SPEECH_POLL_SECONDS"),
    ],
)
def test_settings_that_can_t_work_are_refused_at_load(env, match):
    with pytest.raises(SettingsInvalid, match=match):
        load(env)


def test_local_settings_choose_whisper_and_a_key():
    example = json.loads((SRC / "local.settings.json.example").read_text())["Values"]
    assert (example["STT_ENGINE"], example["OPENAI_AUTH"]) == ("whisper", "key")
    assert load(example).stt_engine == "whisper"


def test_entra_gives_the_sdk_a_token_provider_not_a_key(monkeypatch):
    provider = object()
    monkeypatch.setattr(llm, "entra_token_provider", lambda: provider)
    seen = {}
    monkeypatch.setattr(llm, "OpenAI", lambda **kw: seen.update(kw))
    JsonModel.from_settings(load({"OPENAI_AUTH": "entra", "OPENAI_API_KEY": "must-not-be-used"}))
    assert seen["api_key"] is provider
    JsonModel.from_settings(load({}))
    assert seen["api_key"] == "ollama"


def test_the_sdk_sends_the_provider_s_token_as_a_bearer_on_every_request():
    """openai calls a callable api_key before each request, so a refreshed token is always the one sent."""
    tokens, seen = iter(["first", "second"]), []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["Authorization"])
        return httpx.Response(200, json={"object": "list", "data": []})

    client = OpenAI(
        base_url="https://oai.example/openai/v1/",
        api_key=lambda: next(tokens),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_retries=0,
    )
    client.models.list()
    client.models.list()
    assert seen == ["Bearer first", "Bearer second"]


def test_the_token_provider_asks_for_the_cognitive_services_audience(monkeypatch):
    import azure.identity

    asked = {}
    monkeypatch.setattr(azure.identity, "DefaultAzureCredential", lambda: "credential")
    monkeypatch.setattr(
        azure.identity, "get_bearer_token_provider", lambda cred, *scopes: asked.update(cred=cred, scopes=scopes)
    )
    llm.entra_token_provider()
    assert asked == {"cred": "credential", "scopes": (COGNITIVE_SCOPE,)}
    assert COGNITIVE_SCOPE == "https://cognitiveservices.azure.com/.default"


def test_the_function_app_builds_the_transcriber_the_settings_name(monkeypatch):
    monkeypatch.setenv("SPEECH_ENDPOINT", ENDPOINT)
    monkeypatch.setenv("SPEECH_REGION", "uaenorth")
    monkeypatch.setattr(llm, "entra_token_provider", lambda: lambda: "t")
    function_app._transcriber.cache_clear()
    try:
        made = function_app._transcriber()
    finally:
        function_app._transcriber.cache_clear()
    assert isinstance(made, SpeechTranscriber) and made.remote
    assert (made.origin, made.name) == (ENDPOINT.rstrip("/"), "azure-speech batch 2025-10-15 uaenorth")
