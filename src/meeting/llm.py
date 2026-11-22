"""Structured JSON from any OpenAI-compatible endpoint (D5).

Locally that is Ollama's /v1 API (the key is ignored; `json_schema` becomes a grammar the model must follow). On
Azure it will be Azure OpenAI's v1 endpoint with an Entra ID token and strict structured outputs. Reasoning models
there take `reasoning_effort` and `max_completion_tokens` and reject `temperature` and `max_tokens`; a non-empty
`reasoning_effort` switches the request to that shape (as in Projects 3 and 4). `none` is the exception: a local
model that thinks by default (qwen3.5) is asked not to, in the classic shape (Ollama maps `none` to think=false, D27).
"""

import time
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from meeting.settings import Settings


@dataclass(frozen=True)
class Completion:
    text: str
    seconds: float
    prompt_tokens: int | None
    completion_tokens: int | None
    finish_reason: str | None


class JsonModel:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        max_tokens: int = 1500,
        reasoning_effort: str = "",
        timeout: float = 300.0,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort
        self._client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout, max_retries=0)

    @classmethod
    def from_settings(cls, settings: Settings) -> "JsonModel":
        return cls(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=settings.chat_model,
            max_tokens=settings.summary_max_tokens,
            reasoning_effort=settings.chat_reasoning_effort,
            timeout=settings.openai_timeout,
        )

    def sampling_args(self) -> dict[str, Any]:
        if self.reasoning_effort == "none":
            return {"temperature": 0, "max_tokens": self.max_tokens, "reasoning_effort": "none"}
        if self.reasoning_effort:
            return {"reasoning_effort": self.reasoning_effort, "max_completion_tokens": self.max_tokens}
        return {"temperature": 0, "max_tokens": self.max_tokens}

    def complete_json(self, *, system: str, user: str, schema: dict[str, Any], name: str) -> Completion:
        started = time.perf_counter()
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}},
            **self.sampling_args(),
        )
        choice = response.choices[0]
        usage = response.usage
        return Completion(
            text=choice.message.content or "",
            seconds=round(time.perf_counter() - started, 2),
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            finish_reason=choice.finish_reason,
        )
