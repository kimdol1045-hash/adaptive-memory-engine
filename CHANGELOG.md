# Changelog

## 0.1.2 - 2026-06-11

- Added corpus-free bootstrap MCP mode through `memory mcp stdio`.
- Added MCP tools for agent-led setup: `ame_doctor`, `ame_setup`, `ame_load`, `ame_connect`, and `ame_corpora`.
- Updated `memory connect` so Codex/Claude Code can connect before any corpus exists.
- Added tests for agent bootstrap load and query flow.

## 0.1.1 - 2026-06-11

- Added `memory chat <corpus>` for interactive terminal questions without typing `memory query` each time.
- Updated Korean and English README usage docs to show terminal chat mode and MCP usage more clearly.

## 0.1.0 - 2026-06-11

Initial alpha release.

- Added local-first `memory` CLI for corpus setup, ingestion, retrieval, graph inspection, and export.
- Added Bronze/Silver/Gold document memory pipeline with local LLM assisted Silver extraction.
- Added hardware diagnosis and Ollama model recommendation through `memory doctor` and `memory setup`.
- Added stdio MCP server and client config generation for Codex and Claude Code.
- Added deterministic ingestion fallback for tests and lightweight smoke runs.
- Added macOS, Windows, and Linux runtime path handling.
- Added TestPyPI packaging support and GitHub Actions CI/publish workflows.
