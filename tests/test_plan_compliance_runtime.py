from pathlib import Path
import stat

from typer.testing import CliRunner

from ame.agent.mcp import McpStdioServer
from ame.cli.main import app
from ame.core.corpus import require_corpus
from ame.core.state import CorpusStateStore
from ame.hardware.tier import Tier
from ame.models.registry import ModelRegistry


def test_model_registry_yaml_matches_runtime_schema() -> None:
    registry = ModelRegistry.from_yaml(Path("configs/model-registry.yaml"))

    t1 = registry.for_tier(Tier.T1)

    assert t1.extract.model == "qwen3:8b"
    assert t1.verify.model == "qwen3:8b"
    assert t1.synthesize.model == "qwen3:8b"
    assert t1.embed.model == "nomic-embed-text"
    assert t1.embed.dim == 768


def test_runtime_layout_writes_registry_ontology_and_state_db(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    runner = CliRunner()

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["create", "openclaw"]).exit_code == 0

    home = tmp_path / ".ame"
    corpus_root = home / "corpora" / "openclaw"
    assert (home / "registry.cache.yaml").exists()
    assert stat.S_IMODE(home.stat().st_mode) == 0o700
    assert stat.S_IMODE((home / "tokens").stat().st_mode) == 0o700
    assert stat.S_IMODE((home / "config.toml").stat().st_mode) == 0o600
    assert (corpus_root / "ontology" / "base.yaml").exists()
    assert (corpus_root / "state.db").exists()
    assert CorpusStateStore(corpus_root).read().corpus_id == "openclaw"


def test_doctor_reports_current_connectors_and_model_install_state(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    runner = CliRunner()

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "slack-oauth" in result.output
    assert "Embedding model: nomic-embed-text" in result.output
    assert "Token backend: file" in result.output
    assert "PII redaction: off" in result.output
    assert "Missing recommended local LLM models:" in result.output
    assert "Default AME usage is local-LLM Bronze/Silver/Gold build" in result.output


def test_local_mcp_manifest_and_call(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "openclaw.md").write_text(
        "---\nproject: OpenClaw\n---\n# OpenClaw\nOpenClaw decided to use LightRAG.\n",
        encoding="utf-8",
    )
    runner = CliRunner()

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["create", "openclaw"]).exit_code == 0
    assert runner.invoke(app, ["ingest", "openclaw", str(notes)]).exit_code == 0

    manifest = runner.invoke(app, ["mcp", "manifest", "openclaw"])
    call = runner.invoke(app, ["mcp", "call", "openclaw", "memory_search", '{"query":"LightRAG"}'])

    assert manifest.exit_code == 0
    assert "memory_search" in manifest.output
    assert call.exit_code == 0
    assert "LightRAG" in call.output


def test_mcp_stdio_server_lists_and_calls_tools(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "openclaw.md").write_text(
        "---\nproject: OpenClaw\n---\n# OpenClaw\nOpenClaw decided to use LightRAG.\n",
        encoding="utf-8",
    )
    runner = CliRunner()

    assert runner.invoke(app, ["load", "stdio", str(notes), "--mode", "deterministic"]).exit_code == 0

    server = McpStdioServer(require_corpus("stdio"))
    initialized = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    tools = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    call = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "memory_search", "arguments": {"query": "LightRAG"}},
        }
    )

    assert initialized and initialized["result"]["capabilities"]["tools"] == {}
    assert tools and any(tool["name"] == "memory_search" for tool in tools["result"]["tools"])
    assert call and call["result"]["isError"] is False
    assert "LightRAG" in call["result"]["content"][0]["text"]


def test_bootstrap_mcp_can_load_and_query_without_bound_corpus(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "openclaw.md").write_text(
        "---\nproject: OpenClaw\n---\n# OpenClaw\nOpenClaw decided to use LightRAG.\n",
        encoding="utf-8",
    )

    server = McpStdioServer()
    tools = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    load = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "ame_load",
                "arguments": {"corpus_id": "bootstrap", "source_path": str(notes), "mode": "deterministic"},
            },
        }
    )
    search = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "memory_search", "arguments": {"corpus_id": "bootstrap", "query": "LightRAG"}},
        }
    )

    tool_names = {tool["name"] for tool in tools["result"]["tools"]}  # type: ignore[index]
    assert "ame_doctor" in tool_names
    assert "ame_load" in tool_names
    assert "memory_search" in tool_names
    assert load and load["result"]["isError"] is False
    assert search and search["result"]["isError"] is False
    assert "LightRAG" in search["result"]["content"][0]["text"]


def test_connect_without_corpus_prints_bootstrap_mcp_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    monkeypatch.setattr("ame.cli.main._ame_command", lambda: "/tmp/ame/bin/ame")
    runner = CliRunner()

    result = runner.invoke(app, ["connect", "--client", "codex"])

    assert result.exit_code == 0
    assert '"command": "/tmp/ame/bin/ame"' in result.output
    assert '"args": [' in result.output
    assert '"mcp"' in result.output
    assert '"stdio"' in result.output
