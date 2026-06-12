from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestLlmClient:
    def __init__(self, model: str | None = None, base_url: str | None = None) -> None:
        self.model = model
        self.base_url = base_url

    def complete_json(self, prompt: str, payload: dict) -> dict:
        return {"entities": [], "relations": [], "decisions": []}


@pytest.fixture(autouse=True)
def use_local_test_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ame.pipeline.OllamaClient", TestLlmClient)
