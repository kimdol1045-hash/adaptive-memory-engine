import pytest

from ame.core.errors import UnsupportedHardwareError
from ame.hardware.tier import Tier, decide_tier


def test_decide_tier() -> None:
    assert decide_tier(16) == Tier.T1
    assert decide_tier(32) == Tier.T2
    assert decide_tier(48) == Tier.T3
    assert decide_tier(64) == Tier.T4
    assert decide_tier(128) == Tier.T5


def test_decide_tier_rejects_low_memory() -> None:
    with pytest.raises(UnsupportedHardwareError):
        decide_tier(8)
