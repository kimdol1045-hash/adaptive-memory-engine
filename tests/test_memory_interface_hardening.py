from pathlib import Path

from typer.testing import CliRunner

from ame.cli.main import app
from ame.core.corpus import create_corpus
from ame.core.paths import ensure_runtime_layout
from ame.sdk import Corpus
from memory import Corpus as MemoryCorpus


def test_sdk_retrieve_graph_decisions_and_writeback(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    create_corpus("sdk")
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "openclaw.md").write_text(
        "---\nproject: OpenClaw\n---\n# OpenClaw\nOpenClaw decided to use LightRAG.\n",
        encoding="utf-8",
    )

    corpus = Corpus("sdk")
    report = corpus.ingest(notes)
    assert report.documents == 1
    assert corpus.query("LightRAG").answer
    assert corpus.retrieve("LightRAG").matches
    assert corpus.graph("LightRAG").edges

    write = corpus.write_decision("OpenClaw Memory API 확정", "Agent가 memory.retrieve와 memory.graph를 사용하기 위해서다.", project="OpenClaw")
    assert write.ingested is True
    assert "OpenClaw Memory API 확정" in corpus.decisions(current_only=False).model_dump_json()
    assert corpus.decisions(current_only=False, date_from="2999-01-01").decisions == []
    assert MemoryCorpus is Corpus


def test_cli_retrieve_graph_decisions_and_mcp_writeback(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "openclaw.md").write_text(
        "---\nproject: OpenClaw\n---\n# OpenClaw\nOpenClaw decided to use LightRAG.\n",
        encoding="utf-8",
    )
    runner = CliRunner()

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["create", "cli"]).exit_code == 0
    assert runner.invoke(app, ["ingest", "cli", str(notes)]).exit_code == 0

    retrieve = runner.invoke(app, ["retrieve", "cli", "LightRAG"])
    graph = runner.invoke(app, ["graph", "cli", "LightRAG"])
    decisions = runner.invoke(app, ["decisions", "cli", "--all"])
    write = runner.invoke(
        app,
        [
            "mcp",
            "call",
            "cli",
            "memory_write_decision",
            '{"title":"CLI Memory Interface 확정","rationale":"MCP와 CLI parity 검증을 위해서다.","project":"OpenClaw","source":"mcp-test"}',
        ],
    )
    decisions_filtered = runner.invoke(app, ["mcp", "call", "cli", "memory_decisions", '{"from":"2999-01-01"}'])

    assert retrieve.exit_code == 0
    assert "LightRAG" in retrieve.output
    assert graph.exit_code == 0
    assert "edges" in graph.output
    assert decisions.exit_code == 0
    assert "OpenClaw decided to use LightRAG" in decisions.output
    assert write.exit_code == 0
    assert "CLI Memory Interface 확정" in write.output
    assert decisions_filtered.exit_code == 0
    assert '"decisions": []' in decisions_filtered.output
