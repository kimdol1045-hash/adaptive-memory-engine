from __future__ import annotations

from pydantic import BaseModel

from ame.hardware.profiler import HardwareProfile
from ame.models.registry import ModelRegistry, TierModels


class ModelPlan(BaseModel):
    tier: str
    models: TierModels
    mode: str


class ModelRouter:
    def __init__(self, registry: ModelRegistry):
        self.registry = registry

    def plan(self, profile: HardwareProfile) -> ModelPlan:
        models = self.registry.for_tier(profile.tier)
        mode = "full-local" if profile.ollama_installed else "deterministic"
        return ModelPlan(tier=profile.tier.value, models=models, mode=mode)
