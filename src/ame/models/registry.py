from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from ame.hardware.tier import Tier


class ModelRole(BaseModel):
    model: str
    runtime: str = "ollama"
    fallback: str | None = None
    dim: int | None = None


class TierModels(BaseModel):
    extract: ModelRole
    verify: ModelRole
    synthesize: ModelRole
    embed: ModelRole


DEFAULT_REGISTRY: dict[str, Any] = {
    "T1": {
        "extract": {"model": "qwen3:8b"},
        "verify": {"model": "qwen3:8b"},
        "synthesize": {"model": "qwen3:8b", "fallback": "api"},
        "embed": {"model": "nomic-embed-text"},
    },
    "T2": {
        "extract": {"model": "qwen3:14b-q4"},
        "verify": {"model": "qwen3:14b-q4"},
        "synthesize": {"model": "qwen3:14b-q4"},
        "embed": {"model": "bge-m3", "runtime": "local"},
    },
    "T3": {
        "extract": {"model": "qwen3:30b-a3b"},
        "verify": {"model": "qwen3:30b-a3b"},
        "synthesize": {"model": "qwen3:32b-q4"},
        "embed": {"model": "bge-m3", "runtime": "local"},
    },
    "T4": {
        "extract": {"model": "qwen3:32b-q5"},
        "verify": {"model": "qwen3:32b-q5"},
        "synthesize": {"model": "qwen3:32b-q5"},
        "embed": {"model": "bge-m3", "runtime": "local"},
    },
    "T5": {
        "extract": {"model": "qwen3:70b-q4"},
        "verify": {"model": "qwen3:70b-q4"},
        "synthesize": {"model": "qwen3:70b-q4"},
        "embed": {"model": "bge-m3-large", "runtime": "local"},
    },
}


class ModelRegistry:
    def __init__(self, data: dict[str, Any] | None = None):
        self.data = {tier: self._normalize_tier(models) for tier, models in (data or DEFAULT_REGISTRY).items()}

    @classmethod
    def from_yaml(cls, path: Path) -> "ModelRegistry":
        if not path.exists():
            return cls()
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(data.get("tiers", data))

    def for_tier(self, tier: Tier) -> TierModels:
        return TierModels.model_validate(self.data[tier.value])

    def to_dict(self) -> dict[str, Any]:
        return self.data

    def write_cache(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump({"version": 1, "tiers": self.data}, sort_keys=False), encoding="utf-8")
        return path

    def _normalize_tier(self, tier_data: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(tier_data)
        if "embedding" in normalized and "embed" not in normalized:
            normalized["embed"] = normalized.pop("embedding")
        for role in ["extract", "verify", "synthesize", "embed"]:
            value = normalized.get(role)
            if isinstance(value, str):
                normalized[role] = {"model": value}
        return normalized


def load_default_registry(path: Path | None = None) -> ModelRegistry:
    if path is not None:
        return ModelRegistry.from_yaml(path)

    registry_path = Path("configs/model-registry.yaml")
    if registry_path.exists():
        return ModelRegistry.from_yaml(registry_path)

    return ModelRegistry()
