import re
import shutil
from pathlib import Path

from ame.bronze.store import BronzeStore
from ame.core.corpus import create_corpus, require_corpus
from ame.gold.store import GoldStore
from ame.pipeline import MemoryPipeline
from ame.query.engine import QueryEngine


ROOT = Path(__file__).parents[1]
PRD = ROOT / "tests" / "fixtures" / "adaptive_memory_engine_prd_v2_2_integrated.md"
BENCHMARK = ROOT / "benchmark" / "adaptive_memory_engine_benchmark_part3_negative_hallucination.md"
MEMORY_MINI_DOCS = ROOT / "tests" / "fixtures" / "memory-mini" / "docs"


def test_benchmark_part3_negative_hallucination_passes(tmp_path: Path, monkeypatch) -> None:
    engine = _part3_engine(tmp_path, monkeypatch)

    failed: list[str] = []
    for question in _benchmark_questions(BENCHMARK):
        result = engine.query(question["question"])
        answer = _answer_with_sources(result.answer, result.sources)
        missing = [expression for expression in question["expected"] if not _present(expression, answer)]
        if missing:
            failed.append(question["id"])

    assert failed == []


def test_unknown_queries_do_not_fall_back_to_generic_prd_snippets(tmp_path: Path, monkeypatch) -> None:
    engine = _part3_engine(tmp_path, monkeypatch)

    result = engine.query("Adaptive Memory Engine의 CEO는 누구인가?")

    assert result.answer == "문서상 정의되지 않았다."
    assert result.sources == []
    assert result.raw["answer_builder"] == "unknown_detection"


def _part3_engine(tmp_path: Path, monkeypatch) -> QueryEngine:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    source_dir = tmp_path / "source_docs"
    source_dir.mkdir()
    shutil.copy2(PRD, source_dir / PRD.name)
    for source in sorted(MEMORY_MINI_DOCS.glob("*.md")):
        shutil.copy2(source, source_dir / source.name)

    create_corpus("benchmark-part3")
    MemoryPipeline().ingest("benchmark-part3", source_dir, mode="deterministic")
    corpus_root = require_corpus("benchmark-part3")
    return QueryEngine(BronzeStore(corpus_root), GoldStore(corpus_root))


def _benchmark_questions(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^## (Q\d{3})\s*$", text, flags=re.M))
    questions = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.start() : end]
        questions.append(
            {
                "id": match.group(1),
                "question": _inline_value(block, "Question"),
                "expected": _expected_lines(block),
            }
        )
    return questions


def _inline_value(block: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}:\s*(.+)$", block, flags=re.M)
    return match.group(1).strip() if match else ""


def _expected_lines(block: str) -> list[str]:
    match = re.search(r"^Expected Answer:\s*\n(.*?)(?=^## Q\d{3}\b|^# Category |^# Success Criteria|\Z)", block, flags=re.M | re.S)
    if not match:
        return []
    return [line.strip() for line in match.group(1).splitlines() if line.strip() and line.strip() != "---"]


def _answer_with_sources(answer: str, sources: list[object]) -> str:
    source_text = "\n".join(getattr(source, "document", "") for source in sources)
    return f"{answer}\n{source_text}"


def _present(expression: str, answer: str) -> bool:
    return _normalize(expression) in _normalize(answer)


def _normalize(text: str) -> str:
    return text.casefold().replace(" ", "").replace("\u00a0", "")
