from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO

from pydantic import BaseModel, Field

from ame.agent.memory_api import AgentMemoryAPI


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


class McpStdioServer:
    def __init__(self, corpus_root: Path):
        self.corpus_root = corpus_root
        self.toolbox = LocalMcpToolbox(corpus_root)
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
                "serverInfo": {"name": "adaptive-memory-engine", "version": "0.1.0"},
            }
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [self._tool_for_mcp(tool) for tool in READ_TOOLS]}
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
