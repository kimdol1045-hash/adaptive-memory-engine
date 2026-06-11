import re
import shutil
from pathlib import Path

from ame.bronze.store import BronzeStore
from ame.core.corpus import create_corpus, require_corpus
from ame.gold.store import GoldStore
from ame.pipeline import MemoryPipeline
from ame.query.engine import QueryEngine


ROOT = Path(__file__).parents[1]
PRD = ROOT / "adaptive_memory_engine_prd_v2_2_integrated.md"
BENCHMARK = ROOT / "benchmark" / "adaptive_memory_engine_benchmark_part2_timeline_supersedes.md"
MEMORY_MINI_DOCS = ROOT / "tests" / "fixtures" / "memory-mini" / "docs"


def test_benchmark_part2_timeline_supersedes_passes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    source_dir = tmp_path / "source_docs"
    source_dir.mkdir()
    shutil.copy2(PRD, source_dir / PRD.name)
    for source in sorted(MEMORY_MINI_DOCS.glob("*.md")):
        shutil.copy2(source, source_dir / source.name)

    create_corpus("benchmark-part2")
    MemoryPipeline().ingest("benchmark-part2", source_dir, mode="deterministic")
    corpus_root = require_corpus("benchmark-part2")
    engine = QueryEngine(BronzeStore(corpus_root), GoldStore(corpus_root))

    failed: list[str] = []
    for question in _benchmark_questions(BENCHMARK):
        result = engine.query(question["question"])
        answer = _answer_with_sources(result.answer, result.sources)
        missing = [expression for expression in question["required"] if not _present(expression, answer)]
        forbidden = [expression for expression in question["forbidden"] if _present(expression, answer)]
        if missing or forbidden:
            failed.append(question["id"])

    assert failed == []


def test_part2_ingest_resolves_timeline_currentness(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    source_dir = tmp_path / "source_docs"
    source_dir.mkdir()
    for source in sorted(MEMORY_MINI_DOCS.glob("*.md")):
        shutil.copy2(source, source_dir / source.name)

    create_corpus("memory-mini")
    MemoryPipeline().ingest("memory-mini", source_dir, mode="deterministic")
    timeline = {event.title: event for event in GoldStore(require_corpus("memory-mini")).timeline()}

    assert timeline["GraphRAG 직접 구현 검토"].current is False
    assert timeline["GraphRAG 직접 구현 검토"].valid_to == "2026-06-09"
    assert timeline["GraphRAG 직접 구현 검토"].superseded_by == ["LightRAG 도입 결정"]
    assert timeline["LightRAG 도입 결정"].current is True
    assert timeline["Gold 데이터를 자체 JSON 파일에만 저장"].current is False
    assert timeline["Gold 데이터를 자체 JSON 파일에만 저장"].valid_to == "2026-06-13"
    assert timeline["Gold 데이터를 LightRAG custom_kg로 주입"].current is True


def _benchmark_questions(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^## (Q\d{3})\s*$", text, flags=re.M))
    questions = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.start() : end]
        required = _bullet_section(block, "Must Contain")
        if not required:
            required = _expected_lines(block)
        questions.append(
            {
                "id": match.group(1),
                "question": _section(block, "Question"),
                "required": required,
                "forbidden": _bullet_section(block, "Must Not Contain"),
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


def _expected_lines(block: str) -> list[str]:
    lines = []
    for line in _section(block, "Expected Answer").splitlines():
        cleaned = line.strip().lstrip("→").strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def _answer_with_sources(answer: str, sources: list[object]) -> str:
    source_text = "\n".join(getattr(source, "document", "") for source in sources)
    return f"{answer}\n{source_text}"


def _present(expression: str, answer: str) -> bool:
    return _normalize(expression) in _normalize(answer)


def _normalize(text: str) -> str:
    return text.casefold().replace(" ", "").replace("\u00a0", "")
