from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from ame.core.errors import LlmClientError


class OllamaClient:
    def __init__(self, model: str | None = None, base_url: str | None = None, timeout: int = 300):
        self.model = model or os.environ.get("AME_OLLAMA_MODEL", "qwen3:8b")
        self.base_url = (base_url or os.environ.get("AME_OLLAMA_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.timeout = timeout

    def complete_json(self, prompt: str, payload: dict) -> dict:
        try:
            return self._complete_json_chat(prompt, payload)
        except LlmClientError as chat_error:
            try:
                return self._complete_json_generate(prompt, payload)
            except LlmClientError:
                raise chat_error

    def _complete_json_chat(self, prompt: str, payload: dict) -> dict:
        request_payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"입력 JSON:\n{json.dumps(payload, ensure_ascii=False)}"},
            ],
            "format": "json",
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0,
                "num_ctx": int(os.environ.get("AME_OLLAMA_NUM_CTX", "4096")),
                "num_predict": int(os.environ.get("AME_OLLAMA_NUM_PREDICT", "2048")),
            },
        }
        raw = self._post_json("/api/chat", request_payload)
        message = raw.get("message")
        text = message.get("content") if isinstance(message, dict) else None
        if not isinstance(text, str):
            raise LlmClientError("Ollama chat response did not include message.content.")
        return self._parse_response_json(text)

    def _complete_json_generate(self, prompt: str, payload: dict) -> dict:
        request_payload = {
            "model": self.model,
            "prompt": f"{prompt}\n\n입력 JSON:\n{json.dumps(payload, ensure_ascii=False)}",
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0,
                "num_ctx": int(os.environ.get("AME_OLLAMA_NUM_CTX", "4096")),
                "num_predict": int(os.environ.get("AME_OLLAMA_NUM_PREDICT", "2048")),
            },
        }
        raw = self._post_json("/api/generate", request_payload)
        text = raw.get("response")
        if not isinstance(text, str):
            raise LlmClientError("Ollama response did not include a JSON response string.")
        return self._parse_response_json(text)

    def _post_json(self, endpoint: str, payload: dict) -> dict:
        request = urllib.request.Request(
            f"{self.base_url}{endpoint}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise LlmClientError(f"Ollama request failed: {exc}") from exc
        return raw

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
