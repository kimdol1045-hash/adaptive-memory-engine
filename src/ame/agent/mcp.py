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


SERVER_VERSION = "0.1.10"

MCP_INSTRUCTIONS = "\n".join(
    [
        "Use AME MCP tools before shell commands when the user asks about AME setup, AME local model recommendations, local document memory, local RAG, or Bronze/Silver/Gold memory.",
        "Start AME setup conversations with ame_flow, then use ame_doctor for hardware/model diagnosis.",
        "Use ame_setup with execute=false to show a model download plan. Use execute=true only after explicit user approval.",
        "Use bootstrap MCP for hardware/model diagnosis; do not call corpus-bound tools or example corpus IDs for setup diagnosis.",
        "Do not invent or try sample corpus names such as openclaw unless the user explicitly provided that corpus.",
        "When replying in Korean, use polite '~입니다' and '~습니다' style and handle one flow stage at a time.",
    ]
)


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
        name="ame_flow",
        description="Return the recommended AME setup flow, branching rules, and response templates. Use this before guiding a user through AME setup.",
        input_schema={
            "type": "object",
            "properties": {
                "stage": {
                    "type": "string",
                    "enum": ["all", "diagnose", "model_plan", "model_install", "load", "query"],
                    "description": "Flow stage to return. Defaults to all.",
                },
            },
        },
    ),
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
        if tool_name == "ame_flow":
            return _ame_flow(stage=str(arguments.get("stage") or "all"))
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
        if hasattr(stdin, "buffer") and hasattr(stdout, "buffer"):
            self._run_binary(stdin.buffer, stdout.buffer)
            return
        self._run_text(stdin, stdout)

    def _run_text(self, stdin: TextIO, stdout: TextIO) -> None:
        while not self.should_stop:
            line = stdin.readline()
            if line == "":
                break
            if not line.strip():
                continue
            framed = line.casefold().startswith("content-length:")
            try:
                body = self._read_framed_text(line, stdin) if framed else line
                response = self.handle_line(body)
            except ValueError as exc:
                response = self._error(None, -32700, str(exc))
            self._write_text_response(stdout, response, framed=framed)

    def _run_binary(self, stdin: Any, stdout: Any) -> None:
        while not self.should_stop:
            line = stdin.readline()
            if line == b"":
                break
            if not line.strip():
                continue
            framed = line.lower().startswith(b"content-length:")
            try:
                body = self._read_framed_binary(line, stdin).decode("utf-8") if framed else line.decode("utf-8")
                response = self.handle_line(body)
            except (UnicodeDecodeError, ValueError) as exc:
                response = self._error(None, -32700, str(exc))
            self._write_binary_response(stdout, response, framed=framed)

    def _read_framed_text(self, first_header: str, stdin: TextIO) -> str:
        length = self._content_length_from_header(first_header)
        while True:
            line = stdin.readline()
            if line == "":
                raise ValueError("Unexpected EOF while reading MCP headers")
            if line in {"\n", "\r\n"}:
                break
            length = self._content_length_from_header(line, current=length)
        body = stdin.read(length)
        if len(body) != length:
            raise ValueError("Unexpected EOF while reading MCP body")
        return body

    def _read_framed_binary(self, first_header: bytes, stdin: Any) -> bytes:
        length = self._content_length_from_header(first_header.decode("ascii", errors="replace"))
        while True:
            line = stdin.readline()
            if line == b"":
                raise ValueError("Unexpected EOF while reading MCP headers")
            if line in {b"\n", b"\r\n"}:
                break
            length = self._content_length_from_header(line.decode("ascii", errors="replace"), current=length)
        body = stdin.read(length)
        if len(body) != length:
            raise ValueError("Unexpected EOF while reading MCP body")
        return body

    def _content_length_from_header(self, header: str, *, current: int | None = None) -> int:
        name, sep, value = header.partition(":")
        if not sep:
            return current if current is not None else self._raise_header_error("Invalid MCP header")
        if name.strip().casefold() != "content-length":
            return current if current is not None else self._raise_header_error("MCP Content-Length header is required")
        try:
            length = int(value.strip())
        except ValueError as exc:
            raise ValueError("Invalid MCP Content-Length value") from exc
        if length < 0:
            raise ValueError("Invalid MCP Content-Length value")
        return length

    def _raise_header_error(self, message: str) -> int:
        raise ValueError(message)

    def _write_text_response(self, stdout: TextIO, response: dict[str, Any] | list[dict[str, Any]] | None, *, framed: bool) -> None:
        if response is None:
            return
        payload = json.dumps(response, ensure_ascii=False, separators=(",", ":"), default=str)
        if framed:
            length = len(payload.encode("utf-8"))
            stdout.write(f"Content-Length: {length}\r\n\r\n{payload}")
        else:
            stdout.write(payload + "\n")
        stdout.flush()

    def _write_binary_response(self, stdout: Any, response: dict[str, Any] | list[dict[str, Any]] | None, *, framed: bool) -> None:
        if response is None:
            return
        payload = json.dumps(response, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
        if framed:
            stdout.write(f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii") + payload)
        else:
            stdout.write(payload + b"\n")
        stdout.flush()

    def run_lines(self, stdin: TextIO, stdout: TextIO) -> None:
        for line in stdin:
            response = self.handle_line(line)
            self._write_text_response(stdout, response, framed=False)
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
                "instructions": MCP_INSTRUCTIONS,
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
            return {
                "prompts": [
                    {
                        "name": "ame_setup_flow",
                        "description": "Guide the user through AME setup using AME MCP tools first.",
                        "arguments": [],
                    }
                ]
            }
        if method == "prompts/get":
            return self._get_prompt(params)
        if method == "shutdown":
            self.should_stop = True
            return None
        raise ValueError(f"Unsupported MCP method: {method}")

    def _get_prompt(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        if name != "ame_setup_flow":
            raise ValueError("Unknown prompt")
        return {
            "description": "AME setup flow",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": "AME MCP를 사용해서 단계별로 진행해줘. 먼저 ame_flow를 확인하고, 사양 진단은 ame_doctor로 해줘. 모델 다운로드는 계획만 먼저 보여주고 승인 전에는 실행하지 마.",
                    },
                }
            ],
        }

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


def _ame_flow(*, stage: str = "all") -> dict[str, Any]:
    stages = [
        {
            "stage": "diagnose",
            "user_intents": ["사양 진단해줘", "내 컴퓨터에서 AME가 어떤 모델을 쓰면 좋을지 봐줘"],
            "tool": "ame_doctor",
            "branching": [
                "Ollama가 없으면 로컬 모델 설치 전에 Ollama 설치가 필요하다고 설명합니다.",
                "추천 모델이 이미 설치되어 있으면 model_install을 건너뛰고 load 단계로 이동합니다.",
                "모델이 없으면 model_plan으로 이동하고 다운로드 전에 승인을 요청합니다.",
            ],
            "response_template": [
                "현재 사양 요약: OS, architecture, RAM, available disk.",
                "AME tier: detected tier and why.",
                "추천 모델: extract, verify, synthesize, embedding.",
                "설치 상태: installed models and missing models.",
                "다음 단계: downloads needed or memory load can start.",
            ],
            "output_template": "\n".join(
                [
                    "사양 진단 결과입니다.",
                    "",
                    "- OS/CPU: {os} {architecture}",
                    "- RAM: {ram_gb}GB",
                    "- 사용 가능 디스크: {disk_free_gb}GB",
                    "- AME tier: {tier}",
                    "",
                    "추천 모델은 다음과 같습니다.",
                    "",
                    "- 추출: {extract_model}",
                    "- 검증: {verify_model}",
                    "- 종합: {synthesize_model}",
                    "- 임베딩: {embedding_model}",
                    "",
                    "현재 설치 상태를 보면 {installed_summary}입니다.",
                    "",
                    "다음 단계는 {next_step}입니다.",
                ]
            ),
        },
        {
            "stage": "model_plan",
            "user_intents": ["필요한 모델 먼저 알려줘", "다운로드 전에 계획 보여줘"],
            "tool": "ame_setup with execute=false",
            "branching": [
                "이 단계에서는 모델을 다운로드하지 않습니다.",
                "빠진 모델이 없으면 load 단계로 이동합니다.",
                "빠진 모델이 있으면 model_install 진행 승인을 요청합니다.",
            ],
            "response_template": [
                "다운로드 필요 여부.",
                "다운로드할 모델 목록.",
                "왜 필요한지: extraction, verification, synthesis, embeddings.",
                "예상 영향: disk, time, local-only behavior.",
                "승인 질문: '진행해도 될까요?'",
            ],
            "output_template": "\n".join(
                [
                    "모델 설치 계획입니다. 아직 다운로드는 실행하지 않았습니다.",
                    "",
                    "필요한 모델:",
                    "{missing_models}",
                    "",
                    "이 모델들이 필요한 이유:",
                    "- 추출 모델: 문서에서 엔티티, 관계, 결정, 근거를 뽑기 위해 사용합니다.",
                    "- 검증 모델: 추출된 내용을 원문과 대조해 과한 추론을 줄이는 데 사용합니다.",
                    "- 종합 모델: Bronze/Silver 결과를 Gold 메모리로 정리하는 데 사용합니다.",
                    "- 임베딩 모델: 문서 검색과 RAG 검색에 사용합니다.",
                    "",
                    "진행하면 로컬 디스크와 다운로드 시간이 사용됩니다.",
                    "이 계획대로 모델을 설치해도 될까요?",
                ]
            ),
        },
        {
            "stage": "model_install",
            "user_intents": ["승인할게 설치해줘", "모델 다운로드 진행해줘"],
            "tool": "ame_setup with execute=true",
            "branching": [
                "사용자가 명시적으로 승인한 뒤에만 실행합니다.",
                "설치가 실패하면 실패한 모델을 보고하고 재시도 또는 deterministic fallback 여부를 묻습니다.",
                "설치가 성공하면 load 단계로 이동합니다.",
            ],
            "response_template": [
                "실행 결과: installed, skipped, failed.",
                "현재 준비 상태.",
                "다음 단계: source_path and corpus_id required for memory build.",
            ],
            "output_template": "\n".join(
                [
                    "모델 설치 결과입니다.",
                    "",
                    "- 설치 완료: {installed_models}",
                    "- 이미 있던 모델: {skipped_models}",
                    "- 실패한 모델: {failed_models}",
                    "",
                    "현재 AME는 {readiness} 상태입니다.",
                    "다음 단계로 메모리화할 문서 폴더와 corpus 이름이 필요합니다.",
                ]
            ),
        },
        {
            "stage": "load",
            "user_intents": ["이 폴더를 메모리화해줘", "문서 읽혀서 RAG 구축해줘"],
            "tool": "ame_load",
            "branching": [
                "source_path가 없으면 문서 폴더 경로를 요청합니다.",
                "corpus_id가 없으면 짧은 소문자 corpus 이름을 제안합니다.",
                "구축이 성공하면 query 단계로 이동합니다.",
            ],
            "response_template": [
                "대상 폴더와 corpus_id.",
                "구축 방식: Bronze/Silver/Gold.",
                "처리 결과: documents, nodes, edges, rejected items.",
                "저장 위치 또는 corpus name.",
                "다음 질문 예시.",
            ],
            "output_template": "\n".join(
                [
                    "문서 메모리 구축 결과입니다.",
                    "",
                    "- corpus: {corpus_id}",
                    "- 대상 폴더: {source_path}",
                    "- 구축 방식: Bronze -> Silver -> Gold",
                    "- 처리 문서: {documents}",
                    "- Gold nodes: {gold_nodes}",
                    "- Gold edges: {gold_edges}",
                    "- 제외/실패 항목: {rejected}",
                    "",
                    "이제 `{corpus_id}` 메모리를 기준으로 질문할 수 있습니다.",
                    "예: `{corpus_id} 메모리에서 현재 유효한 결정과 근거를 알려줘.`",
                ]
            ),
        },
        {
            "stage": "query",
            "user_intents": ["구축된 메모리 기준으로 답해줘", "이 문서들에서 결정 근거 찾아줘"],
            "tool": "memory_search or memory_query",
            "branching": [
                "bootstrap mode에서 corpus_id가 없으면 사용할 corpus를 묻거나 ame_corpora를 호출합니다.",
                "명시적으로 구분하지 않는 한 일반 지식이 아니라 메모리 결과를 기준으로 답합니다.",
                "확신도나 근거가 약하면 그 사실을 명확히 말합니다.",
            ],
            "response_template": [
                "짧은 답변.",
                "근거: relevant memory sources or nodes.",
                "확신도와 빈틈.",
                "추가로 확인하면 좋은 질문.",
            ],
            "output_template": "\n".join(
                [
                    "짧게 답하면, {answer}",
                    "",
                    "근거:",
                    "{evidence}",
                    "",
                    "확신도와 빈틈:",
                    "- 확신도: {confidence}",
                    "- 아직 약한 부분: {gaps}",
                    "",
                    "다음으로 확인하면 좋은 질문:",
                    "{follow_up_questions}",
                ]
            ),
        },
    ]
    valid = {item["stage"] for item in stages} | {"all"}
    if stage not in valid:
        raise ValueError("stage must be one of all, diagnose, model_plan, model_install, load, query")
    selected = stages if stage == "all" else [item for item in stages if item["stage"] == stage]
    return {
        "style_rules": [
            "여러 단계를 한 답변에 합치지 말고 한 번에 한 단계만 처리합니다.",
            "한국어 사용자에게는 '~입니다', '~습니다'의 존댓말을 사용합니다.",
            "모델 다운로드 전에는 반드시 계획을 먼저 보여주고 명시적 승인을 받습니다.",
            "AME 설정, 모델 추천, 로컬 문서 메모리 요청은 shell이나 웹 검색보다 AME MCP 도구를 먼저 사용합니다.",
            "사양/모델 진단은 corpus가 필요 없는 bootstrap MCP로 처리하고, openclaw 같은 예시 corpus 이름을 임의로 사용하지 않습니다.",
            "넓은 설명보다 지금 해야 할 다음 행동을 구체적으로 제시합니다.",
            "채팅에서 읽을 수 있게 짧게 답하되, 다음 분기를 바꾸는 도구 결과는 포함합니다.",
        ],
        "flow": selected,
    }
