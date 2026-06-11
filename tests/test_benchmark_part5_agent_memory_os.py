import re
import shutil
from pathlib import Path

from ame.agent.memory_api import AgentMemoryAPI
from ame.bronze.store import BronzeStore
from ame.core.corpus import create_corpus, require_corpus
from ame.gold.store import GoldStore
from ame.pipeline import MemoryPipeline
from ame.query.engine import QueryEngine


ROOT = Path(__file__).parents[1]
PRD = ROOT / "adaptive_memory_engine_prd_v2_2_integrated.md"
BENCHMARK = ROOT / "benchmark" / "adaptive_memory_engine_benchmark_part5_agent_memory_os.md"
MEMORY_MINI_DOCS = ROOT / "tests" / "fixtures" / "memory-mini" / "docs"


def test_benchmark_part5_agent_memory_os_passes(tmp_path: Path, monkeypatch) -> None:
    engine, _ = _part5_engine(tmp_path, monkeypatch)

    failed: list[str] = []
    for question in _benchmark_questions(BENCHMARK):
        result = engine.query(question["question"])
        answer = _answer_with_sources(result.answer, result.sources)
        missing = [expression for expression in question["must_contain"] if not _present(expression, answer)]
        forbidden = [expression for expression in question["must_not_contain"] if _present(expression, answer)]
        if missing or forbidden:
            failed.append(question["id"])

    assert failed == []


def test_agent_memory_api_exposes_mql_diff_and_current_decision(tmp_path: Path, monkeypatch) -> None:
    _, corpus_root = _part5_engine(tmp_path, monkeypatch)
    api = AgentMemoryAPI(corpus_root)

    current = api.current_decision()
    assert "current=false" in current.answer
    assert "LightRAG" in current.answer

    mql = api.mql("FIND decisions WHERE current=true")
    assert mql is not None
    assert "accepted decision" in mql.answer
    assert "current=true" in mql.answer

    why = api.why("LightRAG")
    assert why is not None
    assert "rationale" in why.answer

    diff = api.diff(days=7)
    assert "Gold 데이터를 LightRAG custom_kg로 주입" in diff.accepted_decisions


def test_explainable_answer_contains_trace_metadata(tmp_path: Path, monkeypatch) -> None:
    engine, _ = _part5_engine(tmp_path, monkeypatch)

    result = engine.query("LightRAG가 현재 코어라는 답변을 설명해줘.")

    assert result.raw["answer_builder"] == "memory_os"
    assert result.raw["feature"] == "explainable_answer"
    assert result.raw["decision_chain"] == ["GraphRAG 검토", "LightRAG 도입 결정"]
    assert result.raw["reasoning_depth"] == 2
    assert result.confidence == 0.9


def _part5_engine(tmp_path: Path, monkeypatch) -> tuple[QueryEngine, Path]:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    source_dir = tmp_path / "source_docs"
    source_dir.mkdir()
    shutil.copy2(PRD, source_dir / PRD.name)
    for source in sorted(MEMORY_MINI_DOCS.glob("*.md")):
        shutil.copy2(source, source_dir / source.name)

    create_corpus("benchmark-part5")
    MemoryPipeline().ingest("benchmark-part5", source_dir, mode="deterministic")
    corpus_root = require_corpus("benchmark-part5")
    return QueryEngine(BronzeStore(corpus_root), GoldStore(corpus_root)), corpus_root


def _benchmark_questions(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^## (Q\d{3})\s*$", text, flags=re.M))
    questions = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end]
        questions.append(
            {
                "id": match.group(1),
                "question": _section(block, "Question"),
                "must_contain": _bullet_section(block, "Must Contain"),
                "must_not_contain": _bullet_section(block, "Must Not Contain"),
            }
        )
    return questions


def _section(block: str, title: str) -> str:
    match = re.search(rf"^### {re.escape(title)}\s*\n(.*?)(?=^### |^---\s*$|^## Q\d{{3}}\b|\Z)", block, flags=re.M | re.S)
    if not match:
        return ""
    return match.group(1).strip()


def _bullet_section(block: str, title: str) -> list[str]:
    return [line.removeprefix("-").strip() for line in _section(block, title).splitlines() if line.strip().startswith("-")]


def _answer_with_sources(answer: str, sources: list[object]) -> str:
    source_text = "\n".join(getattr(source, "document", "") for source in sources)
    return f"{answer}\n{source_text}"


def _present(expression: str, answer: str) -> bool:
    return _normalize(expression) in _normalize(answer)


def _normalize(text: str) -> str:
    return text.casefold().replace(" ", "").replace("\u00a0", "")
