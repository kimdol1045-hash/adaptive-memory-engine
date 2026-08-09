from __future__ import annotations

import platform
import shutil
import subprocess
import ctypes
import json
import re
from pathlib import Path

from pydantic import BaseModel

from ame.hardware.tier import Tier, decide_tier


class HardwareProfile(BaseModel):
    os: str
    machine: str
    processor: str
    total_ram_gb: int
    disk_free_gb: int
    ollama_installed: bool
    mlx_available: bool
    tier: Tier


class HardwareProfiler:
    def profile(self, path: Path | None = None) -> HardwareProfile:
        total_ram_gb = self._ram_gb()
        disk_root = path or Path.home()
        return HardwareProfile(
            os=platform.system(),
            machine=platform.machine(),
            processor=platform.processor(),
            total_ram_gb=total_ram_gb,
            disk_free_gb=self._disk_free_gb(disk_root),
            ollama_installed=shutil.which("ollama") is not None,
            mlx_available=self._module_available("mlx"),
            tier=decide_tier(total_ram_gb),
        )

    def _ram_gb(self) -> int:
        system = platform.system()
        try:
            if system == "Darwin":
                return self._darwin_ram_gb()
            if system == "Linux":
                meminfo = Path("/proc/meminfo").read_text(encoding="utf-8")
                for line in meminfo.splitlines():
                    if line.startswith("MemTotal:"):
                        return round(int(line.split()[1]) / 1024**2)
            if system == "Windows":
                return self._windows_ram_gb()
        except (OSError, subprocess.CalledProcessError, ValueError):
            return 16
        return 16

    def _darwin_ram_gb(self) -> int:
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                check=True,
                capture_output=True,
                text=True,
            )
            return round(int(result.stdout.strip()) / 1024**3)
        except (OSError, subprocess.CalledProcessError, ValueError):
            pass

        result = subprocess.run(
            ["system_profiler", "SPHardwareDataType", "-json"],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        rows = payload.get("SPHardwareDataType") or []
        if not rows:
            raise ValueError("system_profiler did not return hardware data")
        match = re.search(r"([\d.]+)\s*(TB|GB|MB)", str(rows[0].get("physical_memory", "")), re.IGNORECASE)
        if not match:
            raise ValueError("system_profiler did not return physical memory")
        value = float(match.group(1))
        unit = match.group(2).upper()
        if unit == "TB":
            value *= 1024
        elif unit == "MB":
            value /= 1024
        return round(value)

    def _windows_ram_gb(self) -> int:
        class MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatusEx()
        status.dwLength = ctypes.sizeof(MemoryStatusEx)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
            return round(status.ullTotalPhys / 1024**3)
        return 16

    def _disk_free_gb(self, path: Path) -> int:
        usage = shutil.disk_usage(path)
        return round(usage.free / 1024**3)

    def _module_available(self, name: str) -> bool:
        try:
            __import__(name)
        except ImportError:
            return False
        return True
