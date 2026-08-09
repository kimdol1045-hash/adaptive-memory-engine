from pathlib import Path

from typer.testing import CliRunner

from ame.bronze.store import BronzeStore
from ame.cli.main import app
from ame.core.state import CorpusStateStore
from ame.gold.store import GoldStore


class FakeLlmClient:
    def __init__(self, model: str | None = None, base_url: str | None = None) -> None:
        self.model = model
        self.base_url = base_url

    def complete_json(self, prompt: str, payload: dict) -> dict:
        return {"entities": [], "relations": [], "decisions": []}


def test_cli_pipeline(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    monkeypatch.setattr("ame.pipeline.OllamaClient", FakeLlmClient)
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
    repeat_ingest = runner.invoke(app, ["ingest", "openclaw", str(notes)])
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
    assert state.last_mode == "llm"
    assert len(state.documents) == 1

    stats = runner.invoke(app, ["stats", "openclaw"])
    inspect_result = runner.invoke(app, ["inspect", "openclaw"])
    lightrag_status = runner.invoke(app, ["lightrag", "status", "openclaw"])
    lightrag_sync = runner.invoke(app, ["lightrag", "sync", "openclaw"])
    assert stats.exit_code == 0
    assert "gold_edges: 4" in stats.output
    assert inspect_result.exit_code == 0
    assert "openclaw.md" in inspect_result.output
    assert lightrag_status.exit_code == 0
    assert "Initialized: True" in lightrag_status.output
    assert "relationships: 4" in lightrag_status.output
    assert lightrag_sync.exit_code == 0
    assert "LightRAG synced:" in lightrag_sync.output
    assert "chunks: 1" in lightrag_sync.output
    assert "relationships: 4" in lightrag_sync.output


def test_cli_chat_keeps_session_open_for_questions(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    monkeypatch.setattr("ame.pipeline.OllamaClient", FakeLlmClient)
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "openclaw.md").write_text(
        "---\nproject: OpenClaw\n---\n# OpenClaw\nOpenClaw decided to use LightRAG.\n",
        encoding="utf-8",
    )
    runner = CliRunner()

    assert runner.invoke(app, ["load", "openclaw", str(notes)]).exit_code == 0
    chat = runner.invoke(app, ["chat", "openclaw"], input="LightRAG\n/exit\n")

    assert chat.exit_code == 0
    assert "AME chat: openclaw" in chat.output
    assert "LightRAG" in chat.output
    assert "bye" in chat.output
