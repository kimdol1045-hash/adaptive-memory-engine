from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, TextIO

from pydantic import BaseModel, Field

from ame.agent.memory_api import AgentMemoryAPI
from ame.core.config import load_config
from ame.core.corpus import create_corpus, require_corpus
from ame.core.paths import ame_home, ensure_runtime_layout
from ame.hardware.profiler import HardwareProfiler
from ame.models.download import OllamaModelInstaller
from ame.models.registry import load_default_registry
from ame.models.router import ModelRouter
from ame.pipeline import MemoryPipeline


SERVER_VERSION = "0.1.5"


class McpToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)


READ_TOOLS = [
    McpToolSpec(
        name="memory_query",
        description="Answer a grounded natural-language memory question.",
        input_schema={"type": "object", "properties": {"question": {"type": "string"}}},
    ),
    McpToolSpec(
        name="memory_search",
        description="Search local memory and return answer, sources, and confidence.",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
    ),
    McpToolSpec(
        name="memory_retrieve",
        description="Retrieve raw matching graph nodes, edges, and documents.",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}, "k": {"type": "integer"}}},
    ),
    McpToolSpec(
        name="memory_graph",
        description="Return graph neighborhood for an entity.",
        input_schema={"type": "object", "properties": {"entity": {"type": "string"}}},
    ),
    McpToolSpec(
        name="memory_decisions",
        description="Return accepted current decisions.",
        input_schema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "from": {"type": "string"},
                "to": {"type": "string"},
                "current_only": {"type": "boolean"},
            },
        },
    ),
    McpToolSpec(
        name="memory_timeline",
        description="Return the decision timeline for a corpus or project.",
        input_schema={"type": "object", "properties": {"project": {"type": "string"}}},
    ),
    McpToolSpec(
        name="memory_why",
        description="Return rationale for a decision.",
        input_schema={"type": "object", "properties": {"decision": {"type": "string"}}},
    ),
    McpToolSpec(
        name="memory_diff",
        description="Return recent memory changes.",
        input_schema={"type": "object", "properties": {"days": {"type": "integer"}}},
    ),
    McpToolSpec(
        name="memory_write_decision",
        description="Write a grounded decision memory.",
        input_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "rationale": {"type": "string"},
                "project": {"type": "string"},
                "source": {"type": "string"},
                "participants": {"type": "array", "items": {"type": "string"}},
            },
        },
    ),
    McpToolSpec(
        name="memory_write_note",
        description="Write a note memory.",
        input_schema={"type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}}},
    ),
]


BOOTSTRAP_TOOLS = [
    McpToolSpec(
        name="ame_doctor",
        description="Diagnose local AME runtime, hardware tier, and recommended local models.",
        input_schema={"type": "object", "properties": {}},
    ),
    McpToolSpec(
        name="ame_setup",
        description="Plan or execute local model installation through Ollama. Use execute=false before asking the user for approval.",
        input_schema={
            "type": "object",
            "properties": {
                "execute": {"type": "boolean", "description": "Pull missing models when true. Defaults to false."},
            },
        },
    ),
    McpToolSpec(
        name="ame_load",
        description="Build Bronze/Silver/Gold memory from a local document folder.",
        input_schema={
            "type": "object",
            "properties": {
                "corpus_id": {"type": "string"},
                "source_path": {"type": "string"},
                "mode": {"type": "string", "enum": ["llm", "deterministic"]},
                "profile": {"type": "string"},
            },
            "required": ["corpus_id", "source_path"],
        },
    ),
    McpToolSpec(
        name="ame_connect",
        description="Return MCP client configuration for a built corpus.",
        input_schema={
            "type": "object",
            "properties": {
                "corpus_id": {"type": "string"},
                "client": {"type": "string", "enum": ["generic", "codex", "claude"]},
            },
            "required": ["corpus_id"],
        },
    ),
    McpToolSpec(
        name="ame_corpora",
        description="List local AME corpora.",
        input_schema={"type": "object", "properties": {}},
    ),
]


class LocalMcpToolbox:
    def __init__(self, corpus_root: Path):
        self.api = AgentMemoryAPI(corpus_root)

    @staticmethod
    def manifest(corpus_id: str) -> dict[str, Any]:
        return {
            "name": "adaptive-memory-engine",
            "transport": "local-stdio-compatible",
            "corpus_id": corpus_id,
            "tools": [tool.model_dump() for tool in READ_TOOLS],
        }

    def call(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        arguments = arguments or {}
        if tool_name == "memory_query":
            return self._dump(self.api.search(str(arguments.get("question", ""))))
        if tool_name == "memory_search":
            return self._dump(self.api.search(str(arguments.get("query", ""))))
        if tool_name == "memory_retrieve":
            return self._dump(self.api.retrieve(str(arguments.get("query", "")), int(arguments.get("k", 8))))
        if tool_name == "memory_graph":
            return self._dump(self.api.graph(str(arguments.get("entity", ""))))
        if tool_name == "memory_decisions":
            if arguments:
                return self._dump(
                    self.api.decisions(
                        arguments.get("project"),
                        bool(arguments.get("current_only", True)),
                        date_from=arguments.get("from") or arguments.get("date_from"),
                        date_to=arguments.get("to") or arguments.get("date_to"),
                    )
                )
            return self._dump(self.api.current_decision())
        if tool_name == "memory_timeline":
            return self._dump(self.api.timeline(arguments.get("project")))
        if tool_name == "memory_why":
            return self._dump(self.api.why(str(arguments.get("decision", ""))))
        if tool_name == "memory_diff":
            return self._dump(self.api.diff(int(arguments.get("days", 7))))
        if tool_name == "memory_write_decision":
            return self._dump(
                self.api.write_decision(
                    title=str(arguments.get("title", "")),
                    rationale=str(arguments.get("rationale", "")),
                    project=arguments.get("project"),
                    participants=arguments.get("participants") or [],
                    source=str(arguments.get("source") or "writeback"),
                )
            )
        if tool_name == "memory_write_note":
            return self._dump(self.api.write_note(str(arguments.get("title", "")), str(arguments.get("content", ""))))
        raise ValueError(f"Unknown MCP tool: {tool_name}")

    def _dump(self, value: Any) -> dict[str, Any]:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if isinstance(value, dict):
            return value
        return {"value": value}


class BootstrapMcpToolbox:
    def __init__(self, corpus_root: Path | None = None):
        self.corpus_root = corpus_root

    @staticmethod
    def manifest(corpus_id: str | None = None) -> dict[str, Any]:
        tools = _tools_for_mode(corpus_bound=corpus_id is not None)
        return {
            "name": "adaptive-memory-engine",
            "transport": "local-stdio-compatible",
            "corpus_id": corpus_id,
            "tools": [tool.model_dump() for tool in tools],
        }

    def call(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        arguments = arguments or {}
        if tool_name == "ame_doctor":
            return self._doctor()
        if tool_name == "ame_setup":
            return self._setup(execute=bool(arguments.get("execute", False)))
        if tool_name == "ame_load":
            corpus_id = str(arguments.get("corpus_id") or "").strip()
            source_path = str(arguments.get("source_path") or "").strip()
            if not corpus_id:
                raise ValueError("ame_load requires corpus_id")
            if not source_path:
                raise ValueError("ame_load requires source_path")
            mode = str(arguments.get("mode") or "llm")
            if mode not in {"llm", "deterministic"}:
                raise ValueError("ame_load mode must be llm or deterministic")
            profile = arguments.get("profile")
            return self._load(corpus_id, Path(source_path).expanduser(), mode=mode, profile=str(profile) if profile else None)
        if tool_name == "ame_connect":
            corpus_id = str(arguments.get("corpus_id") or "").strip()
            if not corpus_id:
                raise ValueError("ame_connect requires corpus_id")
            return self._connect(corpus_id, client=str(arguments.get("client") or "generic"))
        if tool_name == "ame_corpora":
            return self._corpora()
        if self.corpus_root is not None:
            return LocalMcpToolbox(self.corpus_root).call(tool_name, arguments)

        corpus_id = str(arguments.get("corpus_id") or "").strip()
        if not corpus_id:
            raise ValueError(f"{tool_name} requires corpus_id when AME MCP is running in bootstrap mode")
        local_arguments = {key: value for key, value in arguments.items() if key != "corpus_id"}
        return LocalMcpToolbox(require_corpus(corpus_id)).call(tool_name, local_arguments)

    def _doctor(self) -> dict[str, Any]:
        home = ensure_runtime_layout()
        config = load_config()
        profile = HardwareProfiler().profile(home)
        plan = ModelRouter(load_default_registry()).plan(profile)
        install_plan = OllamaModelInstaller(host=config.lightrag.ollama_host, allow_cli_list=True).install_plan(plan, profile)
        return {
            "ame_home": str(home),
            "runtime": "local filesystem",
            "hardware": profile.model_dump(mode="json"),
            "model_plan": plan.model_dump(mode="json"),
            "install_plan": install_plan.model_dump(mode="json"),
            "next_steps": [
                "Ask the user before running ame_setup with execute=true because it downloads local models.",
                "After models are ready, call ame_load with corpus_id and source_path.",
                "After memory is built, answer questions with memory_search or memory_query using that corpus_id.",
            ],
        }

    def _setup(self, *, execute: bool) -> dict[str, Any]:
        home = ensure_runtime_layout()
        config = load_config()
        profile = HardwareProfiler().profile(home)
        plan = ModelRouter(load_default_registry()).plan(profile)
        installer = OllamaModelInstaller(host=config.lightrag.ollama_host, allow_cli_list=True)
        install_plan = installer.install_plan(plan, profile)
        payload: dict[str, Any] = {
            "ame_home": str(home),
            "execute": execute,
            "install_plan": install_plan.model_dump(mode="json"),
        }
        if not profile.ollama_installed:
            payload["status"] = "blocked"
            payload["message"] = "Ollama is not installed. Install Ollama first, then run setup again."
            return payload
        if not install_plan.missing_models:
            payload["status"] = "ready"
            payload["message"] = "Recommended local models are already installed."
            return payload
        if not execute:
            payload["status"] = "planned"
            payload["message"] = "Ask the user for approval before running ame_setup with execute=true."
            return payload
        results = installer.pull(install_plan.missing_models, execute=True, installed=install_plan.installed_models)
        payload["status"] = "executed"
        payload["results"] = [result.model_dump(mode="json") for result in results]
        return payload

    def _load(self, corpus_id: str, source_path: Path, *, mode: str, profile: str | None) -> dict[str, Any]:
        ensure_runtime_layout()
        create_corpus(corpus_id)
        report = MemoryPipeline().ingest(corpus_id, source_path, mode=mode, profile=profile)
        return {
            "corpus_id": corpus_id,
            "source_path": str(source_path),
            "report": report.model_dump(mode="json"),
            "next_steps": [
                f"Use memory_search with corpus_id={corpus_id!r} to answer grounded questions.",
                f"Use ame_connect with corpus_id={corpus_id!r} if the user wants a corpus-bound MCP config.",
            ],
        }

    def _connect(self, corpus_id: str, *, client: str) -> dict[str, Any]:
        require_corpus(corpus_id)
        server = {
            "command": "ame",
            "args": ["mcp", "stdio", corpus_id],
        }
        env = _current_mcp_env()
        if env:
            server["env"] = env
        if client == "generic":
            return server
        if client not in {"codex", "claude"}:
            raise ValueError("client must be generic, codex, or claude")
        return {"mcpServers": {"adaptive-memory-engine": server}}

    def _corpora(self) -> dict[str, Any]:
        home = ensure_runtime_layout()
        corpora_root = home / "corpora"
        corpora = []
        for child in sorted(corpora_root.iterdir()):
            if child.is_dir():
                corpora.append({"corpus_id": child.name, "path": str(child)})
        return {"ame_home": str(home), "corpora": corpora}


class McpStdioServer:
    def __init__(self, corpus_root: Path | None = None):
        self.corpus_root = corpus_root
        self.toolbox = BootstrapMcpToolbox(corpus_root)
        self.should_stop = False

    def run(self, stdin: TextIO | None = None, stdout: TextIO | None = None) -> None:
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        for line in stdin:
            response = self.handle_line(line)
            if response is not None:
                stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":"), default=str) + "\n")
                stdout.flush()
            if self.should_stop:
                break

    def handle_line(self, line: str) -> dict[str, Any] | list[dict[str, Any]] | None:
        if not line.strip():
            return None
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            return self._error(None, -32700, f"Parse error: {exc}")
        return self.handle(payload)

    def handle(self, payload: Any) -> dict[str, Any] | list[dict[str, Any]] | None:
        if isinstance(payload, list):
            responses = [self.handle(item) for item in payload]
            return [response for response in responses if response is not None] or None
        if not isinstance(payload, dict):
            return self._error(None, -32600, "Invalid request")

        request_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params") or {}

        if request_id is None:
            self._handle_notification(method)
            return None

        try:
            result = self._handle_request(str(method), params)
        except ValueError as exc:
            return self._error(request_id, -32602, str(exc))
        except Exception as exc:  # pragma: no cover - defensive JSON-RPC boundary.
            return self._error(request_id, -32603, str(exc))

        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _handle_notification(self, method: Any) -> None:
        if method == "notifications/initialized":
            return
        if method == "notifications/cancelled":
            return

    def _handle_request(self, method: str, params: dict[str, Any]) -> dict[str, Any] | None:
        if method == "initialize":
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "adaptive-memory-engine", "version": SERVER_VERSION},
            }
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [self._tool_for_mcp(tool) for tool in _tools_for_mode(corpus_bound=self.corpus_root is not None)]}
        if method == "tools/call":
            return self._call_tool(params)
        if method == "resources/list":
            return {"resources": []}
        if method == "prompts/list":
            return {"prompts": []}
        if method == "shutdown":
            self.should_stop = True
            return None
        raise ValueError(f"Unsupported MCP method: {method}")

    def _call_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("tools/call requires params.name")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise ValueError("tools/call params.arguments must be an object")

        try:
            result = self.toolbox.call(name, arguments)
            return {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2, default=str)}],
                "isError": False,
            }
        except Exception as exc:
            return {"content": [{"type": "text", "text": str(exc)}], "isError": True}

    def _tool_for_mcp(self, tool: McpToolSpec) -> dict[str, Any]:
        return {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.input_schema,
        }

    def _error(self, request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _tools_for_mode(*, corpus_bound: bool) -> list[McpToolSpec]:
    if corpus_bound:
        return READ_TOOLS
    return BOOTSTRAP_TOOLS + [_with_corpus_argument(tool) for tool in READ_TOOLS]


def _with_corpus_argument(tool: McpToolSpec) -> McpToolSpec:
    schema = json.loads(json.dumps(tool.input_schema))
    properties = schema.setdefault("properties", {})
    properties["corpus_id"] = {"type": "string", "description": "AME corpus id to query."}
    required = schema.setdefault("required", [])
    if "corpus_id" not in required:
        required.append("corpus_id")
    return McpToolSpec(name=tool.name, description=tool.description, input_schema=schema)


def _current_mcp_env() -> dict[str, str]:
    if not os.environ.get("AME_HOME"):
        return {}
    return {"AME_HOME": str(ame_home().expanduser().resolve())}
