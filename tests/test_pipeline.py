from pathlib import Path

from typer.testing import CliRunner

from ame.bronze.store import BronzeStore
from ame.cli.main import app
from ame.core.state import CorpusStateStore
from ame.gold.store import GoldStore


def test_cli_pipeline(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "openclaw.md").write_text(
        "---\nproject: OpenClaw\nauthor: andan\n---\n"
        "# OpenClaw\nOpenClaw decided to use LightRAG.\n[[Adaptive Memory Engine]] #memory\n",
        encoding="utf-8",
    )
    runner = CliRunner()

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["create", "openclaw"]).exit_code == 0
    ingest = runner.invoke(app, ["ingest", "openclaw", str(notes)])
    assert ingest.exit_code == 0
    assert "rejected item" in ingest.output
    query = runner.invoke(app, ["query", "openclaw", "LightRAG"])

    assert query.exit_code == 0
    assert "LightRAG" in query.output
    assert "Sources:" in query.output
    assert "openclaw.md" in query.output

    corpus_root = tmp_path / ".ame" / "corpora" / "openclaw"
    repeat_ingest = runner.invoke(app, ["ingest", "openclaw", str(notes), "--mode", "deterministic"])
    assert repeat_ingest.exit_code == 0

    edges = GoldStore(corpus_root).edges()
    assert {(edge.source, edge.relation, edge.target) for edge in edges} == {
        ("OpenClaw", "USES", "LightRAG"),
        ("OpenClaw", "RELATED_TO", "Adaptive Memory Engine"),
        ("OpenClaw decided to use LightRAG", "MADE_IN", "OpenClaw"),
        ("OpenClaw decided to use LightRAG", "USES", "LightRAG"),
    }
    assert GoldStore(corpus_root).timeline()[0].title == "OpenClaw decided to use LightRAG"
    assert len(list(BronzeStore(corpus_root).list())) == 1

    state = CorpusStateStore(corpus_root).read()
    assert state.last_mode == "deterministic"
    assert len(state.documents) == 1

    stats = runner.invoke(app, ["stats", "openclaw"])
    inspect_result = runner.invoke(app, ["inspect", "openclaw"])
    lightrag_status = runner.invoke(app, ["lightrag", "status", "openclaw"])
    assert stats.exit_code == 0
    assert "gold_edges: 4" in stats.output
    assert inspect_result.exit_code == 0
    assert "openclaw.md" in inspect_result.output
    assert lightrag_status.exit_code == 0
    assert "Initialized: True" in lightrag_status.output
    assert "relationships: 4" in lightrag_status.output
