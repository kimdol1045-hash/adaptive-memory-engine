import json

import pytest

from ame.core.errors import LlmClientError
from ame.models.ollama import OllamaClient


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_ollama_client_parses_fenced_json() -> None:
    parsed = OllamaClient()._parse_response_json('```json\n{"entities": []}\n```')

    assert parsed == {"entities": []}


def test_ollama_client_extracts_json_object_from_text() -> None:
    parsed = OllamaClient()._parse_response_json('Here is the JSON:\n{"entities": [], "relations": []}')

    assert parsed["relations"] == []


def test_ollama_client_rejects_non_object_json() -> None:
    with pytest.raises(LlmClientError):
        OllamaClient()._parse_response_json("[]")


def test_ollama_client_uses_chat_json_without_thinking(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse({"message": {"content": '{"entities": [], "relations": [], "decisions": []}'}})

    monkeypatch.setattr("ame.models.ollama.urllib.request.urlopen", fake_urlopen)

    result = OllamaClient(model="qwen3:8b", base_url="http://ollama.test", timeout=12).complete_json("Prompt", {"content": "x"})

    assert result["entities"] == []
    assert captured["url"] == "http://ollama.test/api/chat"
    assert captured["timeout"] == 12
    assert captured["payload"]["think"] is False
    assert captured["payload"]["format"] == "json"
    assert captured["payload"]["options"]["temperature"] == 0
