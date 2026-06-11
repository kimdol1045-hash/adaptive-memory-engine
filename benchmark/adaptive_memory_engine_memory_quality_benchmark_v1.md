# Adaptive Memory Engine
# Memory Quality Benchmark v1.0

## Purpose

This benchmark evaluates the quality of Adaptive Memory Engine beyond functional Q/A correctness.

Previous benchmarks validated:

- Part 1: Fact / Decision / Reason Recall
- Part 2: Timeline / SUPERSEDES / Current Decision
- Part 3: Negative Recall / Hallucination Resistance
- Part 4: Multi-Hop Reasoning
- Part 5: Agent Memory / Memory OS Foundation

Memory Quality Benchmark v1 validates whether the system remembers accurately.

It measures:

1. Triple Precision
2. Triple Recall
3. Grounding Error Rate
4. Rationale Recall
5. Decision Chain Accuracy

---

# 1. Metric Summary

| Metric | Purpose | Target |
|---|---|---:|
| Triple Precision | 추출된 triple 중 실제로 맞는 비율 | >= 95% |
| Triple Recall | 존재해야 하는 triple 중 실제 추출된 비율 | >= 90% |
| Grounding Error Rate | 답변 claim 중 source에 근거 없는 비율 | <= 1% |
| Rationale Recall | decision의 rationale을 빠뜨리지 않고 회수한 비율 | >= 85% |
| Decision Chain Accuracy | decision chain 순서와 원인-결과 관계 정확도 | >= 90% |

---

# 2. Input Corpus

Benchmark corpus should include:

- PRD v2.2 integrated document
- LightRAG decision document
- GraphRAG considered document
- Obsidian view requirement document
- Local LLM tier decision document
- Superseded storage policy document
- Current storage policy document
- MVP scope summary
- OpenClaw integration spec
- Hermes integration spec

Required minimum corpus:

```text
001_rag_core_considered.md
002_lightrag_selected.md
003_obsidian_required.md
004_model_tier_decision.md
006_superseded_policy.md
007_current_policy.md
010_project_summary.md
adaptive_memory_engine_prd_v2_2_integrated.md
```

---

# 3. Metric 1 — Triple Precision

## Definition

Triple Precision measures how many extracted triples are correct.

```text
Triple Precision = True Positive Triples / Extracted Triples
```

## Target

```text
>= 95%
```

## Triple Format

```json
{
  "subject": "OpenClaw",
  "predicate": "USES",
  "object": "Adaptive Memory Engine",
  "source_id": "adaptive_memory_engine_prd_v2_2_integrated.md#13. OpenClaw Integration Spec",
  "confidence": 0.92
}
```

## Gold Triple Set Examples

### TP-001

Expected Triple:

```text
Adaptive Memory Engine — USES — LightRAG
```

Source Hint:

```text
002_lightrag_selected.md
9.2 LightRAG Integration
```

Pass Condition:

- subject contains Adaptive Memory Engine
- predicate is USES / ADOPTS / SELECTS
- object contains LightRAG
- source points to LightRAG decision or LightRAG integration section

---

### TP-002

Expected Triple:

```text
LightRAG 도입 결정 — SUPERSEDES — GraphRAG 직접 구현 검토
```

Source Hint:

```text
001_rag_core_considered.md
002_lightrag_selected.md
```

Pass Condition:

- subject contains LightRAG decision
- predicate is SUPERSEDES
- object contains GraphRAG considered / GraphRAG direct implementation
- source includes both previous and current decision evidence

---

### TP-003

Expected Triple:

```text
Gold Layer — PRODUCES — Timeline
```

Source Hint:

```text
8.3 Gold Layer
```

Pass Condition:

- subject contains Gold Layer
- predicate is PRODUCES / CREATES / GENERATES
- object contains Timeline

---

### TP-004

Expected Triple:

```text
Gold Layer — PRODUCES — Knowledge Graph
```

Source Hint:

```text
8.3 Gold Layer
```

---

### TP-005

Expected Triple:

```text
OpenClaw — USES — Adaptive Memory Engine
```

Source Hint:

```text
13. OpenClaw Integration Spec
```

---

### TP-006

Expected Triple:

```text
Hermes — USES — Adaptive Memory Engine
```

Source Hint:

```text
14. Hermes Integration Spec
```

---

### TP-007

Expected Triple:

```text
Hardware Adaptive — SELECTS_MODEL_BY — RAM Tier
```

Source Hint:

```text
10. Hardware Adaptive Layer
10.2 RAM Tier
```

---

### TP-008

Expected Triple:

```text
Validation Gate — VALIDATES — Grounding
```

Source Hint:

```text
11.4 Validation Gate
```

---

### TP-009

Expected Triple:

```text
Validation Gate — VALIDATES — Type Gate
```

Source Hint:

```text
11.4 Validation Gate
```

---

### TP-010

Expected Triple:

```text
Obsidian Layer — EXPORTS — Markdown Vault
```

Source Hint:

```text
12. Obsidian Layer
003_obsidian_required.md
```

---

## False Positive Examples

The following triples should be counted as false positives:

```text
Adaptive Memory Engine — USES — Pinecone
Adaptive Memory Engine — USES — Weaviate
Adaptive Memory Engine — USES — Neo4j
Adaptive Memory Engine — IS_PRODUCT_OF — OpenAI
GraphRAG — IS_CURRENT_CORE_OF — Adaptive Memory Engine
Slack Connector — IS_INCLUDED_IN — MVP
Cloud Sync — IS_INCLUDED_IN — MVP
```

---

# 4. Metric 2 — Triple Recall

## Definition

Triple Recall measures how many required gold triples were successfully extracted.

```text
Triple Recall = Extracted Gold Triples / Total Gold Triples
```

## Target

```text
>= 90%
```

## Required Gold Triple Groups

### Group A — Core Architecture

Required Triples:

```text
Adaptive Memory Engine — HAS_LAYER — Bronze
Adaptive Memory Engine — HAS_LAYER — Silver
Adaptive Memory Engine — HAS_LAYER — Gold
Bronze Layer — STORES — Raw Data
Silver Layer — EXTRACTS — Entity
Silver Layer — EXTRACTS — Relation
Silver Layer — EXTRACTS — Decision
Gold Layer — PRODUCES — Knowledge Graph
Gold Layer — PRODUCES — Timeline
Gold Layer — PRODUCES — Supersession Index
```

Minimum Pass:

```text
9 / 10
```

---

### Group B — RAG Core Decision

Required Triples:

```text
GraphRAG 직접 구현 검토 — STATUS — Superseded
LightRAG 도입 결정 — STATUS — Accepted
LightRAG 도입 결정 — SUPERSEDES — GraphRAG 직접 구현 검토
Adaptive Memory Engine — USES — LightRAG
LightRAG — ROLE — Storage/Retrieval Core
```

Minimum Pass:

```text
5 / 5
```

---

### Group C — Storage Policy

Required Triples:

```text
초기 저장 정책 — STATUS — Superseded
현재 저장 정책 — STATUS — Accepted
Gold 데이터를 LightRAG custom_kg로 주입 — SUPERSEDES — Gold 데이터를 자체 JSON 파일에만 저장
Gold Layer — EXPORTS_TO — LightRAG custom_kg
LightRAG custom_kg — CONNECTS_TO — Memory API
```

Minimum Pass:

```text
4 / 5
```

---

### Group D — Agent Integration

Required Triples:

```text
OpenClaw — USES — Memory API
OpenClaw — USES — Adaptive Memory Engine
Hermes — USES — Adaptive Memory Engine
Hermes — REQUIRES — Personal Memory
Agent — CALLS — memory.search
Agent — CALLS — memory.timeline
Agent — CALLS — memory.why
Agent — CALLS — memory.diff
```

Minimum Pass:

```text
7 / 8
```

---

# 5. Metric 3 — Grounding Error Rate

## Definition

Grounding Error Rate measures unsupported claims in generated answers.

```text
Grounding Error Rate = Unsupported Claims / Total Claims
```

## Target

```text
<= 1%
```

## Claim Definition

A claim is any factual assertion in the answer.

Example:

```text
현재 저장·검색 코어는 LightRAG이다.
```

This is one claim.

Example:

```text
GraphRAG는 과거 검토 기록이며 LightRAG 결정에 의해 SUPERSEDES 되었다.
```

This contains two claims:

1. GraphRAG is a past considered option
2. GraphRAG was superseded by LightRAG

## Grounding Rules

A claim is grounded if:

- It is directly supported by retrieved source text
- It is supported by a structured decision object
- It is supported by a SUPERSEDES edge
- It is supported by a timeline/currentness resolver

A claim is ungrounded if:

- It is not present in source text
- It is inferred without explicit support
- It contradicts current decision state
- It cites unrelated source sections

---

## GER Test Cases

### GER-001

Question:

```text
현재 저장·검색 코어는 무엇인가?
```

Expected Claims:

```text
LightRAG is current storage/retrieval core.
GraphRAG was considered before.
GraphRAG is superseded.
```

Required Sources:

```text
001_rag_core_considered.md
002_lightrag_selected.md
```

Pass Condition:

```text
Unsupported Claims = 0
```

---

### GER-002

Question:

```text
Adaptive Memory Engine은 Pinecone을 사용하지?
```

Expected Claims:

```text
No Pinecone usage decision exists.
Current storage/retrieval core is LightRAG.
```

Pass Condition:

```text
Unsupported Claims = 0
Forbidden Claim: Pinecone is used
```

---

### GER-003

Question:

```text
왜 OpenClaw가 LightRAG를 사용하게 되었지?
```

Expected Claims:

```text
GraphRAG was considered.
16GB constraint mattered.
LightRAG was selected.
OpenClaw uses Adaptive Memory Engine as memory layer.
```

Pass Condition:

```text
Unsupported Claims = 0
All claims cite source or decision chain
```

---

### GER-004

Question:

```text
Hermes에서 필요한 Personal Memory Type은?
```

Expected Claims:

```text
Hermes needs Email memory.
Hermes needs Calendar memory.
Hermes needs Meeting memory.
Hermes needs Task memory.
Hermes needs Document memory.
Hermes needs Decision memory.
Hermes needs Contact memory.
Hermes needs Project memory.
```

Pass Condition:

```text
Unsupported Claims = 0
```

---

# 6. Metric 4 — Rationale Recall

## Definition

Rationale Recall measures how many expected rationale items are recovered for a decision.

```text
Rationale Recall = Retrieved Rationale Items / Expected Rationale Items
```

## Target

```text
>= 85%
```

---

## Rationale Sets

### RR-001 — LightRAG Decision

Decision:

```text
LightRAG 도입 결정
```

Expected Rationales:

```text
16GB 환경 대응
검증된 OSS 활용
GraphRAG 직접 구현 대비 구현 범위 축소
빠른 MVP 검증
저장·검색은 LightRAG에 맡기고 추출·검증 계층에 집중
```

Minimum Pass:

```text
4 / 5
```

---

### RR-002 — Local First

Decision / Principle:

```text
Local First
```

Expected Rationales:

```text
개인 데이터 보호
회사 데이터 보호
프로젝트 히스토리 보호
민감 데이터가 클라우드에 기본 저장되지 않음
사용자 데이터 통제권 유지
```

Minimum Pass:

```text
4 / 5
```

---

### RR-003 — Validation First

Decision / Principle:

```text
Validation First
```

Expected Rationales:

```text
LLM 환각 방지
원문 span 기반 검증
Type Gate 기반 관계 검증
Confidence 기반 품질 관리
검증된 사실만 Memory에 저장
```

Minimum Pass:

```text
4 / 5
```

---

### RR-004 — Obsidian Export

Decision:

```text
Obsidian Export 필요
```

Expected Rationales:

```text
사용자는 Graph DB를 직접 보지 않음
Markdown 노트가 사람이 이해하기 쉬움
Gold Memory를 사람이 검토 가능해야 함
Obsidian Vault로 지식 소비 가능
```

Minimum Pass:

```text
3 / 4
```

---

### RR-005 — Slack Connector MVP 제외

Decision:

```text
Slack Connector MVP 제외
```

Expected Rationales:

```text
MVP 범위 최소화
Memory Pipeline 검증이 우선
Markdown/Obsidian 기반 수직 슬라이스 검증이 먼저
Connector Expansion은 이후 단계
```

Minimum Pass:

```text
3 / 4
```

---

# 7. Metric 5 — Decision Chain Accuracy

## Definition

Decision Chain Accuracy measures whether the system reconstructs the correct decision sequence and causal chain.

```text
Decision Chain Accuracy = Correct Chain Steps / Expected Chain Steps
```

## Target

```text
>= 90%
```

---

## Decision Chain Test Cases

### DCA-001 — RAG Core Evolution

Question:

```text
RAG Core 선택은 어떻게 바뀌었지?
```

Expected Chain:

```text
GraphRAG 직접 구현 검토
↓
16GB 환경과 구현 범위 문제 확인
↓
LightRAG 도입 결정
↓
LightRAG가 현재 저장·검색 코어가 됨
```

Minimum Pass:

```text
4 / 4 steps correct
```

---

### DCA-002 — Storage Policy Evolution

Question:

```text
Gold 저장 정책은 어떻게 바뀌었지?
```

Expected Chain:

```text
Gold 데이터를 자체 JSON 파일에만 저장
↓
LightRAG custom_kg 활용 결정
↓
Gold JSON을 custom_kg로 변환
↓
LightRAG와 Memory API에 연결
```

Minimum Pass:

```text
4 / 4 steps correct
```

---

### DCA-003 — OpenClaw Memory Integration

Question:

```text
왜 OpenClaw가 Adaptive Memory Engine을 사용하게 되었지?
```

Expected Chain:

```text
OpenClaw는 장기 기억이 필요함
↓
Adaptive Memory Engine이 Memory Layer 역할을 함
↓
LightRAG가 저장·검색 코어가 됨
↓
OpenClaw Agent가 Memory API를 사용함
```

Minimum Pass:

```text
4 / 4 steps correct
```

---

### DCA-004 — Hermes Memory Integration

Question:

```text
Hermes가 Adaptive Memory Engine과 연결되는 이유는?
```

Expected Chain:

```text
Hermes는 Personal Memory OS를 목표로 함
↓
Email/Calendar/Meeting/Task/Document memory가 필요함
↓
Adaptive Memory Engine이 Personal Memory Layer를 제공함
↓
Hermes가 장기 개인 기억을 사용할 수 있음
```

Minimum Pass:

```text
4 / 4 steps correct
```

---

### DCA-005 — Validation Flow

Question:

```text
검증된 Memory는 어떤 과정을 거쳐 만들어지지?
```

Expected Chain:

```text
Raw Data 저장
↓
Bronze에서 원본 보존
↓
Silver에서 Entity/Relation/Decision 추출
↓
Validation Gate에서 Grounding/Type/Confidence 검증
↓
Gold에서 Knowledge Graph/Timeline 생성
```

Minimum Pass:

```text
5 / 5 steps correct
```

---

# 8. Metric Report Format

The benchmark runner should output:

```json
{
  "benchmark": "memory_quality_benchmark_v1",
  "generated_at": "2026-06-09T00:00:00",
  "corpus_id": "memory-quality-v1",
  "metrics": {
    "triple_precision": {
      "score": 0.96,
      "target": 0.95,
      "passed": true,
      "true_positive": 96,
      "false_positive": 4,
      "extracted_total": 100
    },
    "triple_recall": {
      "score": 0.92,
      "target": 0.90,
      "passed": true,
      "true_positive": 92,
      "false_negative": 8,
      "gold_total": 100
    },
    "grounding_error_rate": {
      "score": 0.007,
      "target": 0.01,
      "passed": true,
      "unsupported_claims": 7,
      "total_claims": 1000
    },
    "rationale_recall": {
      "score": 0.88,
      "target": 0.85,
      "passed": true
    },
    "decision_chain_accuracy": {
      "score": 0.93,
      "target": 0.90,
      "passed": true
    }
  },
  "overall": {
    "passed": true,
    "quality_grade": "A"
  }
}
```

---

# 9. Quality Grade

| Grade | Condition |
|---|---|
| A+ | All metrics pass and Grounding Error Rate <= 0.5% |
| A | All metrics pass |
| B | 4 / 5 metrics pass |
| C | 3 / 5 metrics pass |
| Fail | fewer than 3 metrics pass |

---

# 10. Acceptance Criteria

Memory Quality Benchmark v1 is considered passed if:

```text
Triple Precision >= 95%
Triple Recall >= 90%
Grounding Error Rate <= 1%
Rationale Recall >= 85%
Decision Chain Accuracy >= 90%
```

All five metrics must pass.

---

# 11. Final Interpretation

If the system passes this benchmark, Adaptive Memory Engine can be considered:

```text
Functionally correct
Structurally accurate
Source-grounded
Rationale-aware
Decision-chain aware
```

This means the system is no longer just answering correctly.

It is remembering correctly.
