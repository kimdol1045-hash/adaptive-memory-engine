# Changelog

## 0.1.0 - 2026-06-11

Initial alpha release.

- Added local-first `memory` CLI for corpus setup, ingestion, retrieval, graph inspection, and export.
- Added Bronze/Silver/Gold document memory pipeline with local LLM assisted Silver extraction.
- Added hardware diagnosis and Ollama model recommendation through `memory doctor` and `memory setup`.
- Added stdio MCP server and client config generation for Codex and Claude Code.
- Added deterministic ingestion fallback for tests and lightweight smoke runs.
- Added macOS, Windows, and Linux runtime path handling.
- Added TestPyPI packaging support and GitHub Actions CI/publish workflows.
