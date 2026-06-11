import pytest

from ame.core.errors import LlmClientError
from ame.models.ollama import OllamaClient


def test_ollama_client_parses_fenced_json() -> None:
    parsed = OllamaClient()._parse_response_json('```json\n{"entities": []}\n```')

    assert parsed == {"entities": []}


def test_ollama_client_extracts_json_object_from_text() -> None:
    parsed = OllamaClient()._parse_response_json('Here is the JSON:\n{"entities": [], "relations": []}')

    assert parsed["relations"] == []


def test_ollama_client_rejects_non_object_json() -> None:
    with pytest.raises(LlmClientError):
        OllamaClient()._parse_response_json("[]")
