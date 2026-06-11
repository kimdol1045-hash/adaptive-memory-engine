from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from ame.core.errors import LlmClientError


class OllamaClient:
    def __init__(self, model: str | None = None, base_url: str | None = None, timeout: int = 120):
        self.model = model or os.environ.get("AME_OLLAMA_MODEL", "qwen3:8b")
        self.base_url = (base_url or os.environ.get("AME_OLLAMA_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.timeout = timeout

    def complete_json(self, prompt: str, payload: dict) -> dict:
        request_payload = {
            "model": self.model,
            "prompt": f"{prompt}\n\n입력 JSON:\n{json.dumps(payload, ensure_ascii=False)}",
            "format": "json",
            "stream": False,
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(request_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise LlmClientError(f"Ollama request failed: {exc}") from exc

        text = raw.get("response")
        if not isinstance(text, str):
            raise LlmClientError("Ollama response did not include a JSON response string.")
        return self._parse_response_json(text)

    def _parse_response_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"\A```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```\Z", "", text)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                raise LlmClientError(f"Ollama returned invalid JSON: {text[:200]}") from exc
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError as nested_exc:
                raise LlmClientError(f"Ollama returned invalid JSON: {text[:200]}") from nested_exc
        if not isinstance(parsed, dict):
            raise LlmClientError("Ollama JSON response must be an object.")
        return parsed
