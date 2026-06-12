# Adaptive Memory Engine Core

Adaptive Memory Engine Core turns local documents into Bronze/Silver/Gold memory
and exposes that memory to Codex, Claude Code, or another MCP client.

The preferred UX is agent-first: connect AME through MCP, then ask Codex or
Claude Code to diagnose hardware, recommend models, build memory, and answer
questions in natural language.

Current status: alpha, distributed through PyPI. Current version: `0.1.6`.

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

Print a Codex MCP config and paste it into Codex custom MCP settings:

```bash
ame connect --client codex
```

For Claude Code:

```bash
ame connect --client claude
```

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

## 3. Ask In Natural Language

Then ask Codex or Claude Code:

```text
Diagnose my computer for AME and recommend local models.
If downloads are needed, show me the model plan first.
After I approve, install the models.
Then build memory named my-docs from /Users/me/Documents/planning.
Once memory is built, answer questions from that local memory.
```

After that, ask normally:

```text
What decisions are currently valid?
Why did we choose this architecture?
Which past decisions are now superseded?
```

## MCP Tools

AME exposes these tools to Codex or Claude Code:

- `ame_doctor`: diagnose hardware and local model status
- `ame_setup`: plan or execute recommended model downloads
- `ame_load`: build Bronze/Silver/Gold memory from a folder
- `ame_corpora`: list built corpora
- `memory_search`, `memory_query`: answer from built memory
- `memory_graph`, `memory_decisions`, `memory_timeline`, `memory_why`: structured memory lookup

Model downloads can take time and disk space. The agent should show the plan
first, then run downloads after user approval.

## Manual CLI Use

You can also use AME directly:

```bash
ame doctor
ame setup
ame setup --execute
ame load my-docs ./path/to/markdown-docs
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

If `ame` is not on PATH, reload your shell config:

```bash
source ~/.zshrc
ame --help
ame connect --client codex
```

If the MCP client still cannot find `ame`, include PATH in the generated JSON:

```bash
ame connect --client codex --include-path-env
```

If that still fails, use the previous absolute command mode:

```bash
ame connect --client codex --absolute-command
```

New versions use `ame` as the recommended command because the older `memory`
command can collide with previous installs. `memory` remains as a compatibility
alias, but prefer `ame`.

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
or `ame connect --client claude` and paste the printed config into the client.

## Bronze/Silver/Gold

- Bronze: preserves raw documents.
- Silver: extracts entities, relations, decisions, rationales, and constraints.
- Gold: builds graph, timeline, supersession, and validation views.

Use deterministic mode only for tests or fallback:

```bash
ame load my-docs ./path/to/docs --mode deterministic
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
