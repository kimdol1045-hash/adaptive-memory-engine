# Adaptive Memory Engine Official Benchmark
# Part 2 — Timeline & SUPERSEDES (Q051~Q070)

## 목적

Part 2는 Timeline, SUPERSEDES, Current Decision, Decision History를 검증한다.

---

# Category A — Current Decision

## Q051
### Question
현재 저장·검색 코어는 무엇인가?

### Expected Answer
현재 저장·검색 코어는 LightRAG이다.

GraphRAG 직접 구현 검토는 SUPERSEDES 관계에 의해 대체되었다.

### Must Contain
- LightRAG
- 현재
- SUPERSEDES

### Must Not Contain
- GraphRAG가 현재 코어

---

## Q052
### Question
현재 Gold 저장 정책은 무엇인가?

### Expected Answer
Gold 데이터를 자체 JSON에 저장한 후 LightRAG custom_kg 포맷으로 변환하여 저장한다.

### Must Contain
- Gold
- LightRAG
- custom_kg

---

## Q053
### Question
현재 유효한 Memory Architecture는?

### Expected Answer
Bronze → Silver → Gold → LightRAG → Memory API

### Must Contain
- Bronze
- Silver
- Gold
- LightRAG
- Memory API

---

## Q054
### Question
현재 Memory Layer 구조는?

### Expected Answer
Bronze, Silver, Gold 3계층 구조를 사용한다.

---

## Q055
### Question
현재 Local Model 정책은?

### Expected Answer
Hardware Adaptive 원칙에 따라 RAM 기반 자동 모델 선택을 사용한다.

---

# Category B — SUPERSEDES

## Q056
### Question
GraphRAG 검토는 어떻게 되었지?

### Expected Answer
GraphRAG 직접 구현 검토는 존재했지만 LightRAG 도입 결정에 의해 SUPERSEDES 되었다.

### Must Contain
- GraphRAG
- LightRAG
- SUPERSEDES

---

## Q057
### Question
어떤 결정이 GraphRAG 검토를 대체했지?

### Expected Answer
LightRAG 도입 결정

---

## Q058
### Question
JSON-only 저장 정책은 현재 정책인가?

### Expected Answer
아니다.

LightRAG custom_kg 정책에 의해 대체되었다.

---

## Q059
### Question
SUPERSEDES의 목적은?

### Expected Answer
과거 결정과 현재 결정을 구분하기 위해 사용한다.

---

## Q060
### Question
SUPERSEDES 적용 후 과거 결정은 삭제되는가?

### Expected Answer
아니다.

기록은 유지되며 current=false 상태가 된다.

---

# Category C — Timeline

## Q061
### Question
RAG 코어 선택은 어떤 순서로 진행되었지?

### Expected Answer
GraphRAG 검토

→ LightRAG 채택

→ 현재 정책

---

## Q062
### Question
언제 LightRAG가 채택되었지?

### Expected Answer
LightRAG 도입 결정 시점 이후 현재 정책으로 유지되고 있다.

---

## Q063
### Question
현재 정책 이전에는 무엇이 있었지?

### Expected Answer
GraphRAG 직접 구현 검토

---

## Q064
### Question
Timeline은 무엇을 추적하는가?

### Expected Answer
결정 변경 이력과 정책 변화를 추적한다.

---

## Q065
### Question
Current Decision은 어떻게 계산하는가?

### Expected Answer
SUPERSEDES 되지 않은 accepted decision만 current=true로 간주한다.

---

# Category D — Contradiction Resolution

## Q066
### Question
문서에는 GraphRAG도 있고 LightRAG도 있는데 현재 무엇이 맞지?

### Expected Answer
현재는 LightRAG가 맞다.

GraphRAG는 과거 검토 기록이다.

---

## Q067
### Question
두 문서가 충돌할 때 무엇을 믿어야 하지?

### Expected Answer
최신 accepted decision과 SUPERSEDES 결과를 우선한다.

---

## Q068
### Question
과거 정책과 현재 정책이 다르면?

### Expected Answer
현재 정책을 우선하고 과거 정책은 히스토리로 보존한다.

---

# Category E — Decision History

## Q069
### Question
왜 LightRAG를 선택했지?

### Expected Answer
16GB 환경 대응

검증된 OSS 활용

구현 범위 축소

빠른 MVP 검증

---

## Q070
### Question
LightRAG 선택의 출처는?

### Expected Answer
002_lightrag_selected.md

Architecture Review

PRD 관련 결정 문서

---

# Part 2 Success Criteria

- Timeline Recall >= 85%
- SUPERSEDES Accuracy >= 95%
- Current Decision Accuracy >= 95%
- Contradiction Resolution >= 90%

Sprint 2 통과 시 Adaptive Memory Engine은 Timeline-aware Memory Engine으로 판정한다.
