# Adaptive Memory Engine Core

Adaptive Memory Engine Core turns local documents into Bronze/Silver/Gold memory
and exposes that memory to Codex, Claude Code, or another MCP client.

The preferred UX is agent-first: connect AME through MCP, then ask Codex or
Claude Code to diagnose hardware, recommend models, build memory, and answer
questions in natural language.

Current status: alpha, distributed through PyPI. Current version: `0.1.17`.

## 1. Install

macOS/Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/kimdol1045-hash/adaptive-memory-engine/main/install.sh | bash
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/kimdol1045-hash/adaptive-memory-engine/main/install.ps1 | iex
```

The installer puts AME in `~/.ame` and adds `ame` to PATH. On macOS/Linux, run
the printed `source ...` command once in the current terminal after
installation:

```bash
source ~/.zshrc
```

Manual PyPI install is also available:

```bash
python -m pip install adaptive-memory-engine
```

Even when you only use custom MCP, the AME executable still needs to exist
locally. PyPI/GitHub distributes the package; the MCP client starts a local `ame
mcp stdio` process so AME can read local documents and use local LLMs.

## 2. Connect Codex Or Claude Code

For Codex, one command registers AME MCP in `~/.codex/config.toml`:

```bash
ame connect --client codex
```

Restart Codex after running it.

To preview the Codex MCP config without writing it:

```bash
ame connect --client codex --print-only
```

For Claude Code, one command registers AME in the user-scope MCP settings. Under
the hood it runs Claude Code's official `claude mcp add --scope user
--transport stdio ...` command:

```bash
ame connect --client claude
```

Restart Claude Code after running it, then check `/mcp` for
`adaptive-memory-engine`.

To preview the registration command and JSON without writing Claude Code config:

```bash
ame connect --client claude --print-only
```

`ame connect --client claude` does not only print JSON. If the Claude Code CLI is
installed and `claude` is on PATH, it registers the MCP server automatically. If
the CLI cannot be found, AME prints the command you can run manually.

By default, the `command` field is `ame`, not an absolute executable path.

```json
{
  "command": "ame",
  "args": ["mcp", "stdio"]
}
```

The default config does not include an absolute executable path. The MCP client
does not need the virtual environment to be activated every time.

This works even before a corpus exists. The bootstrap MCP server lets Codex or
Claude Code diagnose hardware, plan model downloads, build memory, and query the
built memory.

## 3. Proceed In Natural Language

Use separate steps instead of one long request.

Start with this exact prompt. It nudges the agent to use AME MCP tools before
shell commands or web search:

```text
Use AME MCP and follow the AME flow step by step.
Start by checking ame_flow, and diagnose hardware with ame_doctor.
For model downloads, first show the plan with ame_setup execute=false.
Do not run execute=true until I explicitly approve it.
```

Then diagnose hardware and model fit:

```text
Diagnose my computer for AME and recommend local models.
```

If downloads are needed, ask for the plan first:

```text
Show me the models to download and why. Do not install yet.
```

After reviewing the plan, approve installation:

```text
Approved. Install the required models.
```

Then build memory from a folder. AME can first call `ame_corpus_suggest` to
decide whether this should update an existing corpus or create a new one. It then
calls `ame_load_plan` to inspect size and risk, and starts `ame_load_auto` or
`ame_load` if the plan looks acceptable:

```text
Build memory named my-docs from /Users/me/Documents/planning.
```

You can also leave corpus classification to AME:

```text
Classify /Users/me/Documents/planning automatically and build memory from it.
```

After memory is built, ask grounded questions:

```text
Using my-docs memory, tell me the current decisions and their rationale.
```

The expected flow is:

```text
ame_flow -> ame_doctor -> ame_setup execute=false -> user approval -> ame_setup execute=true -> ame_corpus_suggest -> ame_load_plan -> ame_load_auto/ame_load -> ame_load_status -> memory_query/memory_search
```

Hardware diagnosis and model recommendation do not require a corpus. Choose a
corpus name only when building memory from documents.

## 4. Response Templates

AME MCP exposes templates through `ame_flow`. To inspect one:

```text
Show me the output_template for the model_plan stage from ame_flow.
```

Recommended diagnosis response:

```text
Hardware diagnosis result.

- OS/CPU: ...
- RAM: ...
- Available disk: ...
- AME tier: ...

Recommended models:

- Extract: ...
- Verify: ...
- Synthesize: ...
- Embedding: ...

Current install status: ...
Next step: ...
```

Recommended model plan response:

```text
Model installation plan. No downloads have been started yet.

Required models:
...

Why these models are needed:
- Extract model: extracts entities, relations, decisions, and rationale.
- Verify model: checks extracted content against source text.
- Synthesize model: turns Bronze/Silver outputs into Gold memory.
- Embedding model: supports document and RAG search.

This will use local disk and download time.
Should I install these models?
```

Recommended load plan response:

```text
Memory build preflight result.

- source path: ...
- source files: ...
- expected Bronze chunks: ...
- expected local LLM calls: ...
- largest chunk: ...
- risk: ...

Recommendation:
...

Should I start building this into a new corpus named `...`?
```

Recommended memory build response:

```text
Memory build result.

- corpus: ...
- source folder: ...
- build path: Bronze -> Silver -> Gold
- status: ...
- job_id: ...
- processed documents: ...
- Gold nodes: ...
- Gold edges: ...
- rejected items: ...

You can now ask questions against this memory.
```

## MCP Tools

AME exposes these tools to Codex or Claude Code:

- `ame_doctor`: diagnose hardware and local model status
- `ame_flow`: return the step-by-step flow and response templates
- `ame_setup`: plan or execute recommended model downloads
- `ame_corpus_suggest`: suggest whether a source path updates an existing corpus or creates a new corpus
- `ame_load_plan`: inspect source size, chunk count, local LLM calls, and load risk before ingest
- `ame_load_auto`: automatically choose a corpus and start a background memory build
- `ame_load`: build Bronze/Silver/Gold memory from a folder
- `ame_load_status`: check long-running memory build jobs and current stage
- `ame_load_cancel`: cancel a background memory build without replacing committed corpus data
- `ame_corpus_status`: inspect corpus state, LightRAG state, and Bronze/Silver/Gold counts
- `ame_cleanup`: remove stale staging folders and optional failed job logs
- `ame_corpora`: list built corpora
- `memory_search`, `memory_query`: answer from built memory
- `memory_graph`, `memory_decisions`, `memory_timeline`, `memory_why`: structured memory lookup

Model downloads can take time and disk space. The agent should show the plan
first, then run downloads after user approval.

Hardware diagnosis and model recommendations should use bootstrap MCP because
they do not require a corpus. During memory build, users can either provide a
corpus name or let AME choose whether to update an existing corpus or create a
new one.

When the same source is ingested again, older Bronze chunks are not deleted.
They are marked inactive and kept as history. Default search and answers use the
latest active Bronze/Silver/Gold view, while previous Silver/Gold data is stored
under corpus history.

## Manual CLI Use

You can also use AME directly:

```bash
ame doctor
ame setup
ame setup --execute
ame suggest ./path/to/markdown-docs
ame plan ./path/to/markdown-docs
ame load-auto ./path/to/markdown-docs
ame load my-docs ./path/to/markdown-docs
ame load-status --corpus-id my-docs
ame chat my-docs
```

Inside chat mode:

```text
ame> What decisions are currently valid?
ame> Why did we choose LightRAG?
ame> /exit
```

## Troubleshooting

The virtual environment is only used to isolate the Python package install. Once
the MCP config is added, Codex or Claude Code launches the `ame` command.

If AME was already installed, upgrade explicitly:

```bash
python -m pip install --upgrade adaptive-memory-engine
ame --version
```

The printed version should match the current README version.

For package metadata, you can also run:

```bash
python -m pip show adaptive-memory-engine
```

If `ame` is not on PATH, reload your shell config:

```bash
source ~/.zshrc
ame --help
ame connect --client codex
```

If Codex still cannot find `ame`, include PATH in the Codex config:

```bash
ame connect --client codex --include-path-env
```

If that still fails, write the absolute executable path into the Codex config:

```bash
ame connect --client codex --absolute-command
```

New versions use `ame` as the recommended command because the older `memory`
command can collide with previous installs. `memory` remains as a compatibility
alias, but prefer `ame`.

If `ame` is still unavailable, the simplest path is the isolated installer:

```bash
curl -fsSL https://raw.githubusercontent.com/kimdol1045-hash/adaptive-memory-engine/main/install.sh | bash
source ~/.zshrc
ame --help
```

## MCP Modes

Bootstrap MCP:

```bash
ame mcp stdio
```

Corpus-bound MCP:

```bash
ame mcp stdio my-docs
```

Most users do not need to run these manually. Use `ame connect --client codex`
or `ame connect --client claude`; AME handles MCP registration for you.

## Bronze/Silver/Gold

- Bronze: preserves raw documents.
- Silver: extracts entities, relations, decisions, rationales, and constraints.
- Gold: builds graph, timeline, supersession, and validation views.

AME memory builds use local LLM mode.

## SDK

```python
from ame.sdk import Corpus
from memory import Corpus
```

## Tests

```bash
pytest
```
