# ADR-0003: Bound local LightRAG generation and make reindexing explicit

- Status: Accepted
- Date: 2026-08-09
- Owners: AME maintainers
- Supersedes: none
- Superseded by: none

## Context

LightRAG defaults can request a large context, enable reranking without a configured reranker, and delegate generation behavior to the Ollama model. A reasoning-capable local model can therefore spend several minutes on keyword or answer generation when `think` and output limits are not explicit. Separately, changing an embedding model or vector dimension requires rebuilding the vector index even when Bronze, Silver, and Gold data remain valid.

## Options considered

1. Keep all LightRAG defaults: simplest, but runtime latency and memory vary by model and unavailable rerankers produce warnings.
2. Hard-code one small context: predictable, but operators cannot tune capable hardware or larger corpora.
3. Expose bounded defaults in `LightRagConfig` and provide an explicit index sync command.

## Decision

- Configure Ollama calls with explicit context size, output limit, and thinking mode.
- Bound query entity, relationship, chunk, and total context budgets through `QueryParam`.
- Disable reranking by default until a reranker function is configured and include references by default.
- Provide `ame lightrag sync <corpus>` to rebuild the configured backend from current active Bronze documents and Gold graph data without rerunning Silver extraction.
- Keep embedding model and dimension project-configurable; an operator changing either value must run the sync command against a new or intentionally rebuilt vector store.
- Constrain the optional LightRAG and Ollama Python dependencies to the API range validated by AME.

## Consequences

- Local query latency and memory use have explicit upper bounds.
- Grounding chunks retain a budget instead of being displaced by graph context.
- Projects with larger contexts can raise the values in `config.toml` deliberately.
- Reindexing is an explicit operational step and may incur embedding cost and latency.

## Verification

- Unit tests assert Ollama keyword arguments, query budgets, reranker behavior, and reference inclusion.
- CLI tests rebuild a corpus through `ame lightrag sync` and verify counts.
- Integration checks should confirm the configured vector dimension in LightRAG storage and complete a grounded query with references.
