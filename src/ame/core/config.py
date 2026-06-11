from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from ame.core.paths import ame_home


class EngineConfig(BaseModel):
    confidence_threshold: float = 0.7


class StorageConfig(BaseModel):
    home: str = "~/Library/Application Support/ame"


class LightRagConfig(BaseModel):
    backend: Literal["auto", "filesystem", "core"] = "auto"
    query_mode: str = "hybrid"
    ollama_host: str = "http://127.0.0.1:11434"
    llm_model: str = "qwen3:8b"
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768
    max_token_size: int = 8192


class SlackConfig(BaseModel):
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8765/slack/oauth/callback"
    scopes: list[str] = Field(
        default_factory=lambda: [
            "channels:read",
            "channels:history",
            "groups:read",
            "groups:history",
        ]
    )


class GoogleConfig(BaseModel):
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8765/google/oauth/callback"
    scopes: list[str] = Field(
        default_factory=lambda: [
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/spreadsheets.readonly",
        ]
    )


class SecurityConfig(BaseModel):
    token_backend: Literal["file", "keychain", "auto"] = "file"
    pii_redaction: Literal["off", "metadata", "content"] = "off"


class AmeConfig(BaseModel):
    engine: EngineConfig = Field(default_factory=EngineConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    lightrag: LightRagConfig = Field(default_factory=LightRagConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)
    google: GoogleConfig = Field(default_factory=GoogleConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)


def load_config(path: Path | None = None) -> AmeConfig:
    config_path = path or ame_home() / "config.toml"
    if not config_path.exists():
        return AmeConfig()
    data: dict[str, Any] = tomllib.loads(config_path.read_text(encoding="utf-8"))
    return AmeConfig.model_validate(data)
