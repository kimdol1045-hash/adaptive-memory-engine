from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


COMMANDS = [
    [sys.executable, str(ROOT / "tools" / "run_benchmark_part1.py")],
    [sys.executable, str(ROOT / "tools" / "run_benchmark_part2.py")],
    [sys.executable, str(ROOT / "tools" / "run_benchmark_part3.py")],
    [sys.executable, str(ROOT / "tools" / "run_benchmark_part4.py")],
    [sys.executable, str(ROOT / "tools" / "run_benchmark_part5.py")],
    [sys.executable, str(ROOT / "tools" / "run_benchmark_part6.py")],
    [sys.executable, str(ROOT / "tools" / "run_memory_quality_benchmark.py")],
]


def main() -> None:
    for command in COMMANDS:
        print(f"$ {' '.join(command)}")
        subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
