import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib import request


class LLMClient(Protocol):
    """Minimal local-LLM interface used by Cortex."""

    def complete(self, messages: Sequence[Mapping[str, str]]) -> str:
        """Return model text for chat-style messages."""


@dataclass(slots=True)
class FakeLLMClient:
    """Deterministic LLM client for tests."""

    responses: list[str]
    requests: list[list[dict[str, str]]] = field(default_factory=list)

    def complete(self, messages: Sequence[Mapping[str, str]]) -> str:
        self.requests.append([dict(message) for message in messages])
        if not self.responses:
            msg = "FakeLLMClient has no queued responses"
            raise RuntimeError(msg)
        return self.responses.pop(0)


@dataclass(frozen=True, slots=True)
class OpenAICompatibleLLMClient:
    """Small OpenAI-compatible chat client for a local endpoint.

    Tests should use FakeLLMClient; this class is only transport glue for later
    local deployments such as llama.cpp or Ollama-compatible gateways.
    """

    base_url: str
    model: str
    api_key: str | None = None
    timeout_seconds: float = 30.0

    def complete(self, messages: Sequence[Mapping[str, str]]) -> str:
        payload = {
            "model": self.model,
            "messages": list(messages),
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            self._chat_completions_url(),
            data=body,
            headers=self._headers(),
            method="POST",
        )
        with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))

        return _extract_chat_content(response_payload)

    def _chat_completions_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


def _extract_chat_content(response_payload: Mapping[str, Any]) -> str:
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        msg = "LLM response missing choices"
        raise ValueError(msg)

    first_choice = choices[0]
    if not isinstance(first_choice, Mapping):
        msg = "LLM response choice has invalid shape"
        raise ValueError(msg)

    message = first_choice.get("message")
    if not isinstance(message, Mapping):
        msg = "LLM response choice missing message"
        raise ValueError(msg)

    content = message.get("content")
    if not isinstance(content, str):
        msg = "LLM response message content must be a string"
        raise ValueError(msg)

    return content
