# Changelog

## 0.1.16 - 2026-06-12

- Add automatic corpus suggestion and `ame_load_auto` so users can provide only a source path while AME decides whether to update an existing corpus or create a new one.
- Treat same-source re-ingest as a versioned update: older Bronze chunks are marked inactive, current Silver/Gold views are rebuilt from the latest source, and previous Silver/Gold data is archived under corpus history.
- Filter inactive Bronze documents from default query results so updated content does not mix with superseded content.
- Add CLI `ame suggest` and `ame load-auto` mirrors for the MCP auto-classification flow.

## 0.1.15 - 2026-06-12

- Add `ame_load_plan` to estimate file count, Bronze chunk count, local LLM calls, runtime risk, and safer load recommendations before ingest starts.
- Add background load progress heartbeats so `ame_load_status` reports the current Bronze/Silver/Gold/LightRAG stage.
- Add `ame_load_cancel`, `ame_corpus_status`, and `ame_cleanup` for stuck job recovery and stale staging cleanup without deleting committed corpora.
- Prefer Ollama `/api/chat` with `think=false`, JSON format, and deterministic options for local LLM extraction, with generate fallback.
- Add CLI mirrors for load planning, load status, load cancel, cleanup, and corpus status.

## 0.1.14 - 2026-06-12

- Make ingest transactional: Bronze/Silver/Gold/LightRAG outputs are staged first and committed only after the full memory build succeeds.
- Roll back failed memory builds so failed 3-layer builds do not leave partial corpus artifacts.
- Hide temporary ingest staging directories from `ame_corpora`.

## 0.1.13 - 2026-06-12

- Process only documents from the current source path during ingest so stale large Bronze documents in the same corpus do not get reprocessed.
- Make local LLM extraction tolerate invalid rows from model JSON output instead of failing the entire document build.
- Mark dead load worker jobs as `stale` instead of leaving them reported as `running`.

## 0.1.12 - 2026-06-12

- Removed deterministic mode from the user-facing CLI and MCP memory-build flow.
- Split large Markdown sections into smaller Bronze chunks so local LLM extraction and embedding stay under model context limits.
- Changed LightRAG embedding token defaults to `2048` and clamp `nomic-embed-text` to that limit even when older configs still say `8192`.
- Increased local Ollama extraction request timeout to reduce false failures on larger planning documents.

## 0.1.11 - 2026-06-12

- Changed MCP `ame_load` in LLM mode to start a background job by default so Codex/Claude tool calls do not time out.
- Added `ame_load_status` for polling long-running Bronze/Silver/Gold memory builds.
- Updated AME flow guidance to wait for load completion before querying a corpus.

## 0.1.10 - 2026-06-12

- Changed `ame connect --client codex` to write the Codex MCP config directly to `~/.codex/config.toml`.
- Added `--print-only` for previewing the Codex MCP TOML without writing user config.
- Added `ame --version` for simple installed-version checks.
- Updated README guidance so Codex setup no longer tells users to paste Claude-style JSON.

## 0.1.9 - 2026-06-12

- Updated the packaged README with cleaner AME MCP flow guidance and response templates.
- Kept troubleshooting focused on user actions instead of internal debugging history.
- Bumped package and MCP server metadata to 0.1.9.

## 0.1.8 - 2026-06-12

- Added standard MCP `Content-Length` stdio framing support while keeping newline JSON-RPC compatibility.
- Added MCP initialize instructions and an `ame_setup_flow` prompt so agents prefer AME MCP tools for AME setup/model/local-memory requests.
- Documented that setup diagnosis should use bootstrap MCP and must not invent example corpus IDs such as `openclaw`.
- Updated package `ame.__version__` to match the published package version.

## 0.1.7 - 2026-06-12

- Added the `ame_flow` MCP tool with stage-by-stage setup branches and response templates.
- Updated README examples to guide users through AME setup as separate natural-language steps.
- Bumped MCP server metadata to 0.1.7.

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
