import json
from pathlib import Path

from typer.testing import CliRunner

from ame.bronze.store import BronzeStore
from ame.cli.main import app
from ame.gold.store import GoldStore
from ame.silver.store import SilverStore


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "memory-mini"
DOCS_ROOT = FIXTURE_ROOT / "docs"


def _ingest_memory_mini(tmp_path: Path, monkeypatch) -> tuple[Path, CliRunner]:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    runner = CliRunner()

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["create", "memory-mini"]).exit_code == 0
    ingest = runner.invoke(app, ["ingest", "memory-mini", str(DOCS_ROOT)])

    assert ingest.exit_code == 0, ingest.output
    assert "Ingested 10 document(s)" in ingest.output
    return tmp_path / ".ame" / "corpora" / "memory-mini", runner


def test_memory_mini_ingest_validation_and_gold(tmp_path: Path, monkeypatch) -> None:
    corpus_root, _ = _ingest_memory_mini(tmp_path, monkeypatch)
    silver = SilverStore(corpus_root)
    gold = GoldStore(corpus_root)

    assert len(list(BronzeStore(corpus_root).list())) == 10

    entity_pairs = {(entity.type, entity.name) for entity in silver.entities()}
    assert {
        ("Project", "Adaptive Memory Engine"),
        ("Tool", "GraphRAG"),
        ("Tool", "LightRAG"),
        ("Tool", "Obsidian"),
        ("Tool", "Qwen3 8B Q4"),
        ("Concept", "Bronze Store"),
        ("Concept", "Silver Extraction"),
        ("Concept", "Validation Gate"),
        ("Concept", "Gold Builder"),
        ("Concept", "LightRAG Adapter"),
        ("Person", "Alice"),
        ("Person", "초기 개발자"),
        ("Issue", "Relation Extraction 잘못된 관계 생성"),
    }.issubset(entity_pairs)

    decisions = {decision.title: decision for decision in silver.decisions()}
    assert decisions["GraphRAG 직접 구현 검토"].status == "proposed"
    assert decisions["LightRAG 도입 결정"].status == "accepted"
    assert decisions["LightRAG 도입 결정"].supersedes == ["GraphRAG 직접 구현 검토"]
    assert decisions["RAM 기반 로컬 LLM 자동 선택"].rationale and "Qwen3 8B Q4" in decisions["RAM 기반 로컬 LLM 자동 선택"].rationale
    assert decisions["Gold 데이터를 LightRAG custom_kg로 주입"].supersedes == ["Gold 데이터를 자체 JSON 파일에만 저장"]
    assert decisions["MVP 범위 확정"].status == "accepted"

    rejected = [
        json.loads(line)
        for line in (corpus_root / "silver" / "rejected.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rejected == [
        {
            "kind": "relation",
            "id": rejected[0]["id"],
            "reason": "validation_failed",
            "subject": "Alice",
            "predicate": "USES",
            "object": "LightRAG",
        }
    ]

    silver_relations = {(relation.subject, relation.predicate, relation.object) for relation in silver.relations()}
    assert {
        ("Adaptive Memory Engine", "USES", "LightRAG"),
        ("LightRAG 도입 결정", "SUPERSEDES", "GraphRAG 직접 구현 검토"),
        ("Gold 데이터를 LightRAG custom_kg로 주입", "SUPERSEDES", "Gold 데이터를 자체 JSON 파일에만 저장"),
        ("Relation Extraction 잘못된 관계 생성", "RELATED_TO", "Validation Gate"),
    }.issubset(silver_relations)

    gold_edges = {(edge.source, edge.relation, edge.target) for edge in gold.edges()}
    assert {
        ("Adaptive Memory Engine", "USES", "LightRAG"),
        ("LightRAG 도입 결정", "SUPERSEDES", "GraphRAG 직접 구현 검토"),
        ("Gold 데이터를 LightRAG custom_kg로 주입", "SUPERSEDES", "Gold 데이터를 자체 JSON 파일에만 저장"),
    }.issubset(gold_edges)
    assert ("Alice", "USES", "LightRAG") not in gold_edges
    assert len(gold.timeline()) == 6
    assert (corpus_root / "gold" / "supersedes.jsonl").read_text(encoding="utf-8").count("SUPERSEDES") == 2


def test_memory_mini_query_answers_and_sources(tmp_path: Path, monkeypatch) -> None:
    _, runner = _ingest_memory_mini(tmp_path, monkeypatch)
    expected_queries = json.loads((FIXTURE_ROOT / "expected" / "expected_queries.json").read_text(encoding="utf-8"))

    for expected in expected_queries:
        result = runner.invoke(app, ["query", "memory-mini", expected["question"]])

        assert result.exit_code == 0, result.output
        for phrase in expected["expected_answer_contains"]:
            assert phrase in result.output
        for source in expected["required_sources"]:
            assert source in result.output
        for phrase in expected.get("expected_answer_not_current", []):
            assert phrase not in result.output

    result = runner.invoke(app, ["query", "memory-mini", "MVP 전에 막아야 하는 high priority 이슈는?"])
    assert result.exit_code == 0, result.output
    for phrase in ["Relation Extraction", "잘못된 관계", "Validation Gate", "high", "009_issue_log.md"]:
        assert phrase in result.output


def test_memory_mini_obsidian_export(tmp_path: Path, monkeypatch) -> None:
    _, runner = _ingest_memory_mini(tmp_path, monkeypatch)
    output_dir = tmp_path / "vault"

    export = runner.invoke(app, ["export", "obsidian", "memory-mini", str(output_dir)])

    assert export.exit_code == 0, export.output
    expected_files = {
        "Projects/Adaptive Memory Engine.md": ["LightRAG", "Markdown", "Obsidian", "Bronze", "Silver", "Gold"],
        "Tools/LightRAG.md": ["저장·검색 코어", "custom_kg", "Adaptive Memory Engine"],
        "Decisions/LightRAG 도입 결정.md": ["GraphRAG 직접 구현", "16GB Mac", "검증된 OSS", "SUPERSEDES"],
        "Decisions/MVP 범위 확정.md": ["Markdown", "Obsidian", "Slack, Jira, GitHub Connector는 MVP 범위에서 제외"],
        "Issues/Relation Extraction 잘못된 관계 생성.md": ["high", "Validation Gate", "Person이 Tool을 USES"],
    }
    for relative_path, phrases in expected_files.items():
        path = output_dir / relative_path
        assert path.exists(), relative_path
        content = path.read_text(encoding="utf-8")
        for phrase in phrases:
            assert phrase in content
