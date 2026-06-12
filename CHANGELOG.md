# Changelog

## 0.1.6 - 2026-06-12

- Switched public install docs from TestPyPI to PyPI.
- Added macOS/Linux and Windows installer scripts for one-command local setup.
- Simplified README around the agent-first MCP flow: install once, connect once, then use Codex/Claude Code in natural language.

## 0.1.5 - 2026-06-12

- Changed MCP config output to use `command: "ame"` by default.
- Added `--include-path-env` for MCP clients that need PATH included in generated config.
- Added `--absolute-command` for users who prefer the previous absolute executable path behavior.

## 0.1.4 - 2026-06-11

- Updated MCP client config generation to use the absolute `ame` executable path.
- Clarified that virtual environments are only for installation isolation; MCP clients do not need the venv activated after config is added.

## 0.1.3 - 2026-06-11

- Added `ame` as the recommended CLI command to avoid collisions with older or unrelated `memory` commands.
- Kept `memory` as a backwards-compatible alias.
- Updated README examples to use `ame` first.

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
