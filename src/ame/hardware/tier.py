from __future__ import annotations

from enum import StrEnum

from ame.core.errors import UnsupportedHardwareError


class Tier(StrEnum):
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"
    T5 = "T5"


def decide_tier(total_ram_gb: int) -> Tier:
    if total_ram_gb < 16:
        raise UnsupportedHardwareError("Adaptive Memory Engine requires at least 16GB RAM for local MVP defaults.")
    if total_ram_gb < 32:
        return Tier.T1
    if total_ram_gb < 48:
        return Tier.T2
    if total_ram_gb < 64:
        return Tier.T3
    if total_ram_gb < 128:
        return Tier.T4
    return Tier.T5
