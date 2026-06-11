from pathlib import Path

from tools.run_benchmark_part6 import run_benchmark


ROOT = Path(__file__).parents[1]
BENCHMARK = ROOT / "benchmark" / "adaptive_memory_engine_benchmark_part6_connectors.md"


def test_benchmark_part6_connectors_passes(tmp_path: Path) -> None:
    payload = run_benchmark(BENCHMARK, tmp_path / "part6", "benchmark-part6")

    assert payload["passed"] == payload["total"] == 15
    assert payload["memory_counts"]["bronze_documents"] == 3
    assert payload["memory_counts"]["silver_decisions"] >= 3
    assert payload["memory_counts"]["silver_rationales"] >= 3
    assert payload["failed_ids"] == []
