import json
import subprocess

import pytest

from ame.core.errors import UnsupportedHardwareError
from ame.hardware.profiler import HardwareProfiler
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


def test_darwin_ram_falls_back_to_system_profiler(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[0] == "sysctl":
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"SPHardwareDataType": [{"physical_memory": "48 GB"}]}),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert HardwareProfiler()._darwin_ram_gb() == 48
    assert calls == [
        ["sysctl", "-n", "hw.memsize"],
        ["system_profiler", "SPHardwareDataType", "-json"],
    ]
