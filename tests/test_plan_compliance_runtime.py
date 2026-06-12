import io
import json
from pathlib import Path
import stat

from typer.testing import CliRunner

from ame import __version__
from ame.agent.mcp import McpStdioServer
from ame.cli.main import app
from ame.core.corpus import require_corpus
from ame.core.state import CorpusStateStore
from ame.hardware.tier import Tier
from ame.models.registry import ModelRegistry


class FakeLlmClient:
    def __init__(self, model: str | None = None, base_url: str | None = None) -> None:
        self.model = model
        self.base_url = base_url

    def complete_json(self, prompt: str, payload: dict) -> dict:
        return {
            "entities": [
                {"type": "Project", "name": "OpenClaw", "span": "OpenClaw", "confidence": 0.9},
                {"type": "Tool", "name": "LightRAG", "span": "LightRAG", "confidence": 0.9},
            ],
            "relations": [{"subject": "OpenClaw", "predicate": "USES", "object": "LightRAG", "confidence": 0.9}],
            "decisions": [],
        }


def test_model_registry_yaml_matches_runtime_schema() -> None:
    registry = ModelRegistry.from_yaml(Path("configs/model-registry.yaml"))

    t1 = registry.for_tier(Tier.T1)

    assert t1.extract.model == "qwen3:8b"
    assert t1.verify.model == "qwen3:8b"
    assert t1.synthesize.model == "qwen3:8b"
    assert t1.embed.model == "nomic-embed-text"
    assert t1.embed.dim == 768


def test_cli_version_option_reports_package_version() -> None:
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == __version__


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
    monkeypatch.setattr("ame.pipeline.OllamaClient", FakeLlmClient)
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
    monkeypatch.setattr("ame.pipeline.OllamaClient", FakeLlmClient)
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "openclaw.md").write_text(
        "---\nproject: OpenClaw\n---\n# OpenClaw\nOpenClaw decided to use LightRAG.\n",
        encoding="utf-8",
    )
    runner = CliRunner()

    assert runner.invoke(app, ["load", "stdio", str(notes)]).exit_code == 0

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
    assert "Use AME MCP tools before shell commands" in initialized["result"]["instructions"]
    assert tools and any(tool["name"] == "memory_search" for tool in tools["result"]["tools"])
    assert call and call["result"]["isError"] is False
    assert "LightRAG" in call["result"]["content"][0]["text"]


def test_mcp_stdio_accepts_content_length_framing() -> None:
    server = McpStdioServer()
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, separators=(",", ":"))
    stdin = io.StringIO(f"Content-Length: {len(body.encode('utf-8'))}\r\n\r\n{body}")
    stdout = io.StringIO()

    server.run(stdin, stdout)

    raw = stdout.getvalue()
    assert raw.startswith("Content-Length: ")
    _headers, payload = raw.split("\r\n\r\n", 1)
    response = json.loads(payload)
    assert response["result"]["serverInfo"]["name"] == "adaptive-memory-engine"
    assert response["result"]["serverInfo"]["version"] == "0.1.16"
    assert "Use AME MCP tools before shell commands" in response["result"]["instructions"]


def test_mcp_exposes_ame_setup_prompt() -> None:
    server = McpStdioServer()

    prompts = server.handle({"jsonrpc": "2.0", "id": 1, "method": "prompts/list", "params": {}})
    prompt = server.handle({"jsonrpc": "2.0", "id": 2, "method": "prompts/get", "params": {"name": "ame_setup_flow"}})

    assert prompts and prompts["result"]["prompts"][0]["name"] == "ame_setup_flow"
    assert prompt and "AME MCP를 사용해서" in prompt["result"]["messages"][0]["content"]["text"]


def test_bootstrap_mcp_can_load_and_query_without_bound_corpus(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    monkeypatch.setattr("ame.pipeline.OllamaClient", FakeLlmClient)
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
                "arguments": {"corpus_id": "bootstrap", "source_path": str(notes), "mode": "llm", "background": False},
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
    assert "ame_flow" in tool_names
    assert "ame_corpus_suggest" in tool_names
    assert "ame_load_auto" in tool_names
    assert "ame_load_plan" in tool_names
    assert "ame_load" in tool_names
    assert "ame_load_status" in tool_names
    assert "ame_load_cancel" in tool_names
    assert "ame_corpus_status" in tool_names
    assert "ame_cleanup" in tool_names
    assert "memory_search" in tool_names
    assert load and load["result"]["isError"] is False
    assert search and search["result"]["isError"] is False
    assert "LightRAG" in search["result"]["content"][0]["text"]


def test_bootstrap_mcp_starts_llm_load_as_background_job(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))

    def fake_start_load_job(corpus_id: str, source_path: Path, *, mode: str, profile: str | None) -> dict:
        return {
            "job_id": "load-project-20260612000000-test",
            "corpus_id": corpus_id,
            "source_path": str(source_path),
            "mode": mode,
            "profile": profile,
        }

    monkeypatch.setattr("ame.agent.mcp.start_load_job", fake_start_load_job)
    server = McpStdioServer()

    load = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "ame_load",
                "arguments": {"corpus_id": "project", "source_path": str(tmp_path), "mode": "llm"},
            },
        }
    )

    assert load and load["result"]["isError"] is False
    text = load["result"]["content"][0]["text"]
    assert '"status": "started"' in text
    assert '"background": true' in text
    assert "ame_load_status" in text
    assert "load_plan" in text


def test_bootstrap_mcp_load_plan_warns_for_large_sources(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    source = tmp_path / "large.md"
    source.write_text("# Large\n\n" + ("OpenClaw uses LightRAG.\n\n" * 9000), encoding="utf-8")
    server = McpStdioServer()

    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "ame_load_plan", "arguments": {"source_path": str(source)}},
        }
    )

    assert response and response["result"]["isError"] is False
    text = response["result"]["content"][0]["text"]
    assert '"status": "planned"' in text
    assert '"risk": "high"' in text
    assert "bronze_chunks" in text


def test_bootstrap_mcp_can_suggest_corpus_without_user_classification(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    source = tmp_path / "planning"
    source.mkdir()
    (source / "plan.md").write_text("# Plan\nOpenClaw uses LightRAG.\n", encoding="utf-8")
    server = McpStdioServer()

    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "ame_corpus_suggest", "arguments": {"source_path": str(source)}},
        }
    )

    assert response and response["result"]["isError"] is False
    text = response["result"]["content"][0]["text"]
    assert '"status": "suggested"' in text
    assert '"action": "create_new"' in text
    assert '"selected_corpus_id": "planning"' in text


def test_bootstrap_mcp_reports_load_job_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    from ame.agent.load_jobs import write_job

    write_job(
        {
            "job_id": "load-project-20260612000000-test",
            "kind": "load",
            "status": "completed",
            "corpus_id": "project",
            "source_path": str(tmp_path),
            "mode": "llm",
            "report": {"documents": 2, "gold_nodes": 3, "gold_edges": 4, "rejected": 0},
        }
    )
    server = McpStdioServer()

    status = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "ame_load_status",
                "arguments": {"job_id": "load-project-20260612000000-test"},
            },
        }
    )

    assert status and status["result"]["isError"] is False
    text = status["result"]["content"][0]["text"]
    assert '"status": "completed"' in text
    assert "memory_search" in text


def test_bootstrap_mcp_reports_running_load_progress(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    from ame.agent.load_jobs import mark_load_progress, write_job

    write_job(
        {
            "job_id": "load-project-20260612000000-progress",
            "kind": "load",
            "status": "starting",
            "corpus_id": "project",
            "source_path": str(tmp_path),
            "mode": "llm",
        }
    )
    mark_load_progress(
        "load-project-20260612000000-progress",
        {"stage": "silver_extraction", "current": 2, "total": 10, "source_id": "a.md"},
    )
    server = McpStdioServer()

    status = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "ame_load_status",
                "arguments": {"job_id": "load-project-20260612000000-progress"},
            },
        }
    )

    assert status and status["result"]["isError"] is False
    text = status["result"]["content"][0]["text"]
    assert "silver_extraction" in text
    assert '"current": 2' in text


def test_bootstrap_mcp_can_cancel_starting_load_job(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    from ame.agent.load_jobs import write_job

    write_job(
        {
            "job_id": "load-project-20260612000000-cancel",
            "kind": "load",
            "status": "starting",
            "corpus_id": "project",
            "source_path": str(tmp_path),
            "mode": "llm",
        }
    )
    server = McpStdioServer()

    cancelled = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "ame_load_cancel",
                "arguments": {"job_id": "load-project-20260612000000-cancel"},
            },
        }
    )

    assert cancelled and cancelled["result"]["isError"] is False
    text = cancelled["result"]["content"][0]["text"]
    assert '"status": "cancelled"' in text


def test_bootstrap_mcp_cleanup_removes_staging_dirs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    runner = CliRunner()
    assert runner.invoke(app, ["init"]).exit_code == 0
    staging = tmp_path / ".ame" / "corpora" / ".project.ingest-test"
    staging.mkdir(parents=True)
    server = McpStdioServer()

    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "ame_cleanup", "arguments": {"corpus_id": "project"}},
        }
    )

    assert response and response["result"]["isError"] is False
    assert not staging.exists()


def test_bootstrap_mcp_marks_dead_load_job_as_stale(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    from ame.agent.load_jobs import write_job

    write_job(
        {
            "job_id": "load-project-20260612000000-stale",
            "kind": "load",
            "status": "running",
            "pid": 999999999,
            "corpus_id": "project",
            "source_path": str(tmp_path),
            "mode": "llm",
        }
    )
    server = McpStdioServer()

    status = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "ame_load_status",
                "arguments": {"job_id": "load-project-20260612000000-stale"},
            },
        }
    )

    assert status and status["result"]["isError"] is False
    text = status["result"]["content"][0]["text"]
    assert '"status": "stale"' in text
    assert "worker process is no longer running" in text


def test_bootstrap_mcp_exposes_flow_response_templates(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    server = McpStdioServer()

    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "ame_flow", "arguments": {"stage": "model_plan"}},
        }
    )

    assert response and response["result"]["isError"] is False
    text = response["result"]["content"][0]["text"]
    assert "model_plan" in text
    assert "response_template" in text
    assert "output_template" in text
    assert "이 단계에서는 모델을 다운로드하지 않습니다" in text
    assert "모델 설치 계획입니다" in text


def test_connect_without_corpus_writes_codex_mcp_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("AME_HOME", raising=False)
    runner = CliRunner()

    result = runner.invoke(app, ["connect", "--client", "codex"])

    assert result.exit_code == 0
    assert "Codex MCP config updated:" in result.output
    config_text = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert "[mcp_servers.adaptive-memory-engine]" in config_text
    assert 'command = "ame"' in config_text
    assert 'args = ["mcp", "stdio"]' in config_text
    assert "PATH" not in config_text


def test_connect_can_print_codex_mcp_config_without_writing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("AME_HOME", raising=False)
    runner = CliRunner()

    result = runner.invoke(app, ["connect", "--client", "codex", "--print-only"])

    assert result.exit_code == 0
    assert "[mcp_servers.adaptive-memory-engine]" in result.output
    assert 'command = "ame"' in result.output
    assert not (tmp_path / ".codex" / "config.toml").exists()


def test_connect_can_include_path_env_when_requested(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    monkeypatch.setattr("ame.cli.main._ame_path_env", lambda: "/tmp/ame/bin:/usr/bin")
    runner = CliRunner()

    result = runner.invoke(app, ["connect", "--client", "codex", "--include-path-env"])

    assert result.exit_code == 0
    config_text = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert 'command = "ame"' in config_text
    assert "[mcp_servers.adaptive-memory-engine.env]" in config_text
    assert 'PATH = "/tmp/ame/bin:/usr/bin"' in config_text


def test_connect_can_print_absolute_command_when_requested(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    monkeypatch.setattr("ame.cli.main._ame_command", lambda: "/tmp/ame/bin/ame")
    runner = CliRunner()

    result = runner.invoke(app, ["connect", "--client", "codex", "--absolute-command"])

    assert result.exit_code == 0
    config_text = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert 'command = "/tmp/ame/bin/ame"' in config_text
