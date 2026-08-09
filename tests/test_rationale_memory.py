import shutil
from pathlib import Path

from ame.agent.memory_api import AgentMemoryAPI
from ame.core.corpus import create_corpus, require_corpus
from ame.gold.store import GoldStore
from ame.pipeline import MemoryPipeline
from ame.silver.store import SilverStore


ROOT = Path(__file__).parents[1]
PRD = ROOT / "tests" / "fixtures" / "adaptive_memory_engine_prd_v2_2_integrated.md"
MEMORY_MINI_DOCS = ROOT / "tests" / "fixtures" / "memory-mini" / "docs"


def test_rationale_memory_is_extracted_and_linked(tmp_path: Path, monkeypatch) -> None:
    corpus_root = _ingest_quality_corpus(tmp_path, monkeypatch)
    silver = SilverStore(corpus_root)
    gold = GoldStore(corpus_root)

    rationales = silver.rationales()
    by_decision = {}
    for rationale in rationales:
        by_decision.setdefault(rationale.decision_title, set()).add(rationale.rationale_text)

    assert {
        "16GB 환경 대응",
        "검증된 OSS 활용",
        "GraphRAG 직접 구현 대비 구현 범위 축소",
        "빠른 MVP 검증",
        "저장·검색은 LightRAG에 맡기고 추출·검증 계층에 집중",
    }.issubset(by_decision["LightRAG 도입 결정"])
    assert len(by_decision["Local First"]) == 5
    assert len(by_decision["Validation First"]) == 5
    assert len(by_decision["Obsidian Export 필요"]) == 4
    assert len(by_decision["Slack Connector MVP 제외"]) == 4

    edges = {(edge.source, edge.relation, edge.target) for edge in gold.edges()}
    assert any(source == "LightRAG 도입 결정" and relation == "HAS_RATIONALE" for source, relation, _ in edges)
    assert any(target.startswith("Rationale Category:") for _, relation, target in edges if relation == "RELATED_TO")


def test_why_uses_rationale_memory_first(tmp_path: Path, monkeypatch) -> None:
    corpus_root = _ingest_quality_corpus(tmp_path, monkeypatch)
    why = AgentMemoryAPI(corpus_root).why("LightRAG")

    assert why is not None
    assert "rationale memory" in why.answer
    assert "16GB 환경 대응" in why.answer
    assert "GraphRAG 직접 구현 대비 구현 범위 축소" in why.answer
    assert "저장·검색은 LightRAG에 맡기고 추출·검증 계층에 집중" in why.answer


def _ingest_quality_corpus(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    source_dir = tmp_path / "source_docs"
    source_dir.mkdir()
    shutil.copy2(PRD, source_dir / PRD.name)
    for source in sorted(MEMORY_MINI_DOCS.glob("*.md")):
        shutil.copy2(source, source_dir / source.name)

    create_corpus("rationale-memory")
    MemoryPipeline().ingest("rationale-memory", source_dir, mode="deterministic")
    return require_corpus("rationale-memory")
