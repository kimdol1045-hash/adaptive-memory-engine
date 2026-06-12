# Adaptive Memory Engine Core

Adaptive Memory Engine Core turns local documents into Bronze/Silver/Gold memory
and exposes that memory to Codex, Claude Code, or another MCP client.

The preferred UX is agent-first: connect AME through MCP, then ask Codex or
Claude Code to diagnose hardware, recommend models, build memory, and answer
questions in natural language.

Current status: alpha, distributed through TestPyPI. Current beta version: `0.1.4`.

## 1. Install

No `pipx` required. Copy and run:

```bash
python3 -m venv ~/.ame
source ~/.ame/bin/activate

python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  adaptive-memory-engine==0.1.4
```

Check the install:

```bash
hash -r
which ame
ame --help
```

`which ame` should point to something like `~/.ame/bin/ame`.

## 2. Connect Codex Or Claude Code

Print a Codex MCP config:

```bash
ame connect --client codex
```

Print a Claude Code MCP config:

```bash
ame connect --client claude
```

Add the printed JSON to the client MCP settings.
The `command` field uses an absolute path such as `~/.ame/bin/ame`, so the MCP
client does not need the virtual environment to be activated every time.

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
the MCP config is added, Codex or Claude Code launches `ame` through the absolute
path in that config.

If `ame` is not found, reactivate the virtual environment:

```bash
source ~/.ame/bin/activate
hash -r
which ame
ame --help
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
