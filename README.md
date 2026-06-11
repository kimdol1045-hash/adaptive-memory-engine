# Adaptive Memory Engine Core

Standalone terminal package for the Adaptive Memory Engine. This folder contains
only the engine code, CLI, examples, configs, benchmarks, and engine tests. The
Chronicle app, web UI, service layer, and Chronicle-specific tests are not
included.

## Platform Support

AME is designed to run on macOS and Windows through the same `memory` CLI.

- macOS: primary development target, default runtime path is `~/Library/Application Support/ame`.
- Windows: supported runtime path is `%LOCALAPPDATA%\AdaptiveMemoryEngine`.
- Linux: supported for local filesystem usage through `$XDG_DATA_HOME/ame` or `~/.local/share/ame`.

Ollama must be installed and available on `PATH` for `memory setup --execute` to download local models.

## Install

Current status: alpha release distributed through TestPyPI.

Beta package from TestPyPI:

```bash
pipx install adaptive-memory-engine \
  --pip-args="--index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/"
```

From source:

```bash
git clone https://github.com/kimdol1045-hash/adaptive-memory-engine.git
cd adaptive-memory-engine
python3 -m pip install -e ".[dev]"
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
export AME_HOME="$PWD/.ame"
```

## Basic CLI Flow

Target user flow:

```text
Open Claude Code / Codex terminal
  -> install AME
  -> diagnose hardware
  -> recommend local LLMs
  -> download models
  -> load documents
  -> build Bronze/Silver/Gold RAG memory
  -> connect via MCP
  -> ask Claude Code / Codex using the built memory pool
```

```bash
memory init
memory doctor
memory setup
memory setup --execute
memory create openclaw
memory ingest openclaw ./examples/notes --mode llm
memory stats openclaw
memory inspect openclaw
memory query openclaw "OpenClaw LightRAG"
memory export obsidian openclaw ./exports/openclaw-vault
```

If you want the shortest local-first flow, use `load` to initialize, create,
and ingest in one step after model setup:

```bash
memory setup --execute
memory load my-docs ./path/to/markdown-docs
memory retrieve my-docs "What decisions are current?"
memory connect my-docs --client codex
```

## Claude Code / Codex via MCP

Use the CLI for setup and ingestion, then run the stdio MCP server for editor
or agent clients:

```bash
export AME_HOME="$PWD/.ame"
memory setup --execute
memory load my-docs ./path/to/markdown-docs
memory mcp stdio my-docs
```

To print the client config snippet:

```bash
memory connect my-docs --client codex
memory connect my-docs --client claude
```

The underlying MCP server command shape is:

```json
{
  "command": "memory",
  "args": ["mcp", "stdio", "my-docs"],
  "env": {
    "AME_HOME": "/absolute/path/to/.ame"
  }
}
```

Available MCP tools include `memory_search`, `memory_retrieve`,
`memory_graph`, `memory_decisions`, `memory_timeline`, `memory_why`,
`memory_diff`, `memory_write_decision`, and `memory_write_note`.

The default AME product flow is local-LLM first: hardware profiling selects
recommended local models, `memory setup --execute` pulls them through Ollama,
and `memory load` builds Bronze/Silver/Gold memory with LLM-assisted Silver
extraction.

MCP transport itself is only the connection layer. It does not replace the
local memory build; it exposes the built local memory to Claude Code, Codex, or
another MCP client.

Layer responsibility:

- Bronze: raw document preservation, no LLM required.
- Silver: structured entity/relation/decision extraction, local LLM by default.
- Gold: graph, timeline, ontology, supersession, and validation built from Silver.

Use `memory load --mode deterministic` only for a lightweight fallback or tests.

See `docs/product_user_flow.md` for the intended end-to-end CLI product flow.
See `docs/release_distribution_plan.md` for the external release plan.

## LLM Extraction

LLM extraction mode uses Ollama by default:

```bash
AME_OLLAMA_MODEL=qwen3:8b memory ingest openclaw ./examples/notes --mode llm
```

Optional LightRAG Core support:

```bash
pip install -e ".[lightrag]"
```

Then set `$AME_HOME/config.toml`:

```toml
[lightrag]
backend = "core"
query_mode = "hybrid"
llm_model = "qwen3:8b"
embedding_model = "nomic-embed-text"
embedding_dim = 768
max_token_size = 8192
```

## SDK

```python
from ame.sdk import Corpus
from memory import Corpus
```

## Tests

```bash
pytest
```

Use a small smoke test when you only want to verify the terminal package:

```bash
pytest tests/test_pipeline.py tests/test_query_engine.py
```
