import re
from pathlib import Path

from typer.testing import CliRunner

from ame.cli.main import app
from ame.connectors.obsidian import ObsidianConnector


ROOT = Path(__file__).parents[1]
PRD = ROOT / "tests" / "fixtures" / "adaptive_memory_engine_prd_v2_2_integrated.md"
BENCHMARK = ROOT / "benchmark" / "adaptive_memory_engine_benchmark_part1_v4_2_scoring_friendly.md"


def test_prd_is_indexed_by_markdown_sections() -> None:
    refs = ObsidianConnector().scan(PRD)
    source_ids = {ref.source_id for ref in refs}

    assert "adaptive_memory_engine_prd_v2_2_integrated.md#8.1 Bronze Layer" in source_ids
    assert "adaptive_memory_engine_prd_v2_2_integrated.md#8.2 Silver Layer" in source_ids
    assert "adaptive_memory_engine_prd_v2_2_integrated.md#8.3 Gold Layer" in source_ids


def test_benchmark_part1_fact_recall_passes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    runner = CliRunner()
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["create", "benchmark"]).exit_code == 0
    ingest = runner.invoke(app, ["ingest", "benchmark", str(PRD)])
    assert ingest.exit_code == 0, ingest.output

    questions = _benchmark_questions(BENCHMARK)[:15]
    failed: list[str] = []
    for question in questions:
        result = runner.invoke(app, ["query", "benchmark", question["question"]])
        assert result.exit_code == 0, result.output
        if not _passes_groups(result.output, question["groups"]):
            failed.append(question["id"])

    assert failed == []


def test_benchmark_part1_decision_recall_passes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    runner = CliRunner()
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["create", "benchmark"]).exit_code == 0
    ingest = runner.invoke(app, ["ingest", "benchmark", str(PRD)])
    assert ingest.exit_code == 0, ingest.output

    questions = _benchmark_questions(BENCHMARK)[15:35]
    failed: list[str] = []
    for question in questions:
        result = runner.invoke(app, ["query", "benchmark", question["question"]])
        assert result.exit_code == 0, result.output
        if not _passes_groups(result.output, question["groups"]):
            failed.append(question["id"])

    assert failed == []


def test_benchmark_part1_reason_recall_passes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    runner = CliRunner()
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["create", "benchmark"]).exit_code == 0
    ingest = runner.invoke(app, ["ingest", "benchmark", str(PRD)])
    assert ingest.exit_code == 0, ingest.output

    questions = _benchmark_questions(BENCHMARK)[35:50]
    failed: list[str] = []
    for question in questions:
        result = runner.invoke(app, ["query", "benchmark", question["question"]])
        assert result.exit_code == 0, result.output
        if not _passes_groups(result.output, question["groups"]):
            failed.append(question["id"])

    assert failed == []


def _benchmark_questions(path: Path) -> list[dict]:
    blocks = re.split(r"(?=^## Q\d{3}\b)", path.read_text(encoding="utf-8"), flags=re.M)
    questions = []
    for block in blocks:
        header = re.match(r"^## (Q\d{3})\s*$", block, flags=re.M)
        if not header:
            continue
        questions.append(
            {
                "id": header.group(1),
                "question": _section(block, "Question"),
                "groups": _groups(block),
            }
        )
    return questions


def _section(block: str, title: str) -> str:
    match = re.search(rf"^### {re.escape(title)}\s*\n(.*?)(?=^### |^---\s*$|^## Q\d{{3}}\b|\Z)", block, flags=re.M | re.S)
    if not match:
        return ""
    return match.group(1).strip()


def _groups(block: str) -> list[list[str]]:
    groups = []
    for line in _section(block, "Must Contain Groups").splitlines():
        match = re.match(r"\s*-\s*Group\s+\d+:\s*(.+)$", line.strip())
        if match:
            groups.append([part.strip() for part in match.group(1).split("|") if part.strip()])
    return groups


def _passes_groups(answer: str, groups: list[list[str]]) -> bool:
    return all(any(_present(expression, answer) for expression in group) for group in groups)


def _present(expression: str, answer: str) -> bool:
    expr = _normalize(expression)
    normalized_answer = _normalize(answer)
    if expr in normalized_answer:
        return True
    synonyms = {
        "저장·검색": ["저장검색", "storage/retrieval", "storageandretrieval"],
        "그래프db": ["그래프데이터베이스", "graphdb"],
        "3계층": ["bronzesilvergold", "bronze/silver/gold", "bronze→silver→gold"],
        "memorypipeline": ["3계층memorypipeline", "bronze/silver/gold", "bronze→silver→gold"],
    }
    return any(_normalize(alias) in normalized_answer for alias in synonyms.get(expr, []))


def _normalize(text: str) -> str:
    return text.casefold().replace(" ", "").replace("\u00a0", "")
