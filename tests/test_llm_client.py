import json
from urllib.error import URLError

import pytest

from fh_agent.planner.llm_client import (
    FakeLLMClient,
    OpenAICompatibleLLMClient,
    _extract_chat_content,
)


def test_fake_llm_client_returns_queued_response_and_records_request() -> None:
    client = FakeLLMClient(responses=['{"next_goal":"test"}'])

    response = client.complete([{"role": "user", "content": "hello"}])

    assert response == '{"next_goal":"test"}'
    assert client.requests == [[{"role": "user", "content": "hello"}]]


def test_fake_llm_client_raises_when_no_response_is_queued() -> None:
    client = FakeLLMClient(responses=[])

    with pytest.raises(RuntimeError, match="no queued responses"):
        client.complete([{"role": "user", "content": "hello"}])


def test_openai_compatible_client_prepares_local_chat_completion_request(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeHTTPResponse:
        def __enter__(self) -> "FakeHTTPResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {"choices": [{"message": {"content": '{"selected_skill":"continue_dialogue"}'}}]}
            ).encode("utf-8")

    def fake_urlopen(http_request: object, timeout: float) -> FakeHTTPResponse:
        captured["url"] = http_request.full_url
        captured["method"] = http_request.get_method()
        captured["headers"] = dict(http_request.header_items())
        captured["body"] = json.loads(http_request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeHTTPResponse()

    monkeypatch.setattr("fh_agent.planner.llm_client.request.urlopen", fake_urlopen)
    client = OpenAICompatibleLLMClient(
        base_url="http://127.0.0.1:11434/v1",
        model="local-model",
        api_key="test-key",
        timeout_seconds=2.0,
    )

    response = client.complete([{"role": "user", "content": "Plan."}])

    assert response == '{"selected_skill":"continue_dialogue"}'
    assert captured["url"] == "http://127.0.0.1:11434/v1/chat/completions"
    assert captured["method"] == "POST"
    assert captured["timeout"] == 2.0
    assert captured["body"] == {
        "model": "local-model",
        "messages": [{"role": "user", "content": "Plan."}],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }


def test_openai_compatible_client_does_not_hide_transport_errors(monkeypatch) -> None:
    def fake_urlopen(http_request: object, timeout: float) -> object:
        raise URLError("network unavailable")

    monkeypatch.setattr("fh_agent.planner.llm_client.request.urlopen", fake_urlopen)
    client = OpenAICompatibleLLMClient(base_url="http://127.0.0.1:11434/v1", model="local")

    with pytest.raises(URLError):
        client.complete([{"role": "user", "content": "Plan."}])


def test_extract_chat_content_rejects_invalid_response_shape() -> None:
    with pytest.raises(ValueError, match="missing choices"):
        _extract_chat_content({})
