# Architecture Decision Records

AME의 장기적인 구조 결정은 이 디렉터리에 기록합니다. Accepted ADR은 구현 제약이며, 방향을 바꿀 때 기존 기록을 덮어쓰지 않고 새 ADR로 supersede합니다.

## Workflow

1. 변경과 관련된 Accepted ADR을 먼저 확인합니다.
2. `template.md`를 복사해 Context, Options, Decision, Consequences, Verification을 작성합니다.
3. 검토가 끝나기 전에는 `Proposed`, 구현 기준이 되면 `Accepted`로 표시합니다.
4. 결정을 변경하면 새 ADR의 `Supersedes`와 이전 ADR의 `Superseded by`를 연결합니다.

## Index

| ID | Title | Status |
|---|---|---|
| [0001](0001-configured-runtime-model.md) | Configured runtime model is authoritative | Accepted |
| [0002](0002-darwin-memory-detection-fallback.md) | macOS memory detection uses a verified fallback | Accepted |
| [0003](0003-bounded-lightrag-runtime.md) | Bound local LightRAG generation and make reindexing explicit | Accepted |
