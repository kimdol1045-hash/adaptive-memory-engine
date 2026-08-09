# ADR-0001: Configured runtime model is authoritative

- Status: Accepted
- Date: 2026-08-09
- Owners: AME maintainers
- Supersedes: none
- Superseded by: none

## Context

AME exposes `lightrag.llm_model` in `config.toml`, and the LightRAG adapter uses that value. The Silver extraction pipeline previously ignored it and selected the hardware registry's extract model at runtime. A single ingest could therefore use a different model than the deployment configuration and LightRAG backend.

## Options considered

1. Always route from detected hardware: automatic, but overrides an operator's explicit deployment choice.
2. Remove the configuration field: avoids conflicting authorities, but prevents stable project-specific model selection.
3. Use hardware routing for diagnosis and setup recommendations, and use `config.toml` as the runtime authority.

## Decision

`MemoryPipeline` creates its default Ollama client from `lightrag.llm_model` and `lightrag.ollama_host`. `ame doctor`, `ame setup`, and `ame models` may continue to use hardware tiers to recommend and install models. Passing an explicit `llm_client` to the SDK remains the highest-precedence test or application override.

## Consequences

- Silver extraction and LightRAG use the same configured model.
- Projects can pin a model for reproducible runs even when hardware changes.
- Operators must update `config.toml` after choosing a recommendation; hardware detection no longer silently changes the ingest model.

## Verification

- The pipeline test writes a non-default `llm_model` and asserts that the constructed Ollama client receives it.
- An integration check should run an ingest with a configured installed model and confirm the Ollama request model.
