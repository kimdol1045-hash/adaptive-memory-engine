# Adaptive Memory Engine Official Benchmark
# Part 4 — Multi-Hop & Cross-Document Reasoning (Q101~Q120)

## Goal

검증 대상:
- Multi-Hop Reasoning
- Cross-Document Reasoning
- Cross-Decision Reasoning
- Cause → Effect Analysis
- Architecture Impact Analysis

---

# Category A — Multi-Hop Decision Chain (Q101~Q105)

## Q101
Question:
왜 OpenClaw가 LightRAG를 사용하게 되었지?

Expected Answer:
GraphRAG 검토 → 16GB 제약 확인 → LightRAG 채택 → OpenClaw Memory Layer 적용

## Q102
Question:
LightRAG 선택이 Memory Architecture에 어떤 영향을 주었지?

Expected Answer:
Gold → LightRAG custom_kg → Memory API → OpenClaw/Hermes 연결

## Q103
Question:
Local First와 Hardware Adaptive는 어떤 관계가 있지?

Expected Answer:
로컬 실행 → 하드웨어 다양성 → RAM Tier → 자동 모델 선택

## Q104
Question:
Validation First가 필요한 이유와 결과는?

Expected Answer:
환각 방지 → Grounding → Type Gate → 신뢰 가능한 Memory 구축

## Q105
Question:
Memory Schema는 왜 핵심 자산이 되었지?

Expected Answer:
LightRAG는 교체 가능하지만 Memory Schema는 모든 계층의 공통 언어이기 때문이다.

---

# Category B — Cross Document Reasoning (Q106~Q110)

## Q106
Question:
LightRAG 결정과 MVP 범위는 어떤 관계가 있지?

Expected Answer:
빠른 MVP 검증을 위해 GraphRAG 대신 LightRAG를 채택했다.

## Q107
Question:
Slack Connector 제외와 MVP 전략은 어떤 관계인가?

Expected Answer:
Connector 확장보다 Memory Pipeline 검증이 우선이었다.

## Q108
Question:
OpenClaw와 Hermes는 어떤 공통점을 가지는가?

Expected Answer:
둘 다 Adaptive Memory Engine을 장기 기억 계층으로 사용한다.

## Q109
Question:
Gold Layer와 Timeline은 어떤 관계인가?

Expected Answer:
Gold Layer가 Timeline과 SUPERSEDES 정보를 생성한다.

## Q110
Question:
Decision 객체와 Timeline의 관계는?

Expected Answer:
Decision 객체는 Timeline 위에서 변화와 대체 관계를 추적한다.

---

# Category C — Cause & Effect (Q111~Q115)

## Q111
Question:
왜 GraphRAG를 포기했지?

Expected Answer:
구현 범위가 크고 16GB 환경에 비효율적이어서 LightRAG로 전환했다.

## Q112
Question:
왜 LightRAG를 채택했지?

Expected Answer:
16GB 대응, 검증된 OSS, 구현 범위 축소, 빠른 MVP 검증.

## Q113
Question:
왜 Obsidian Export가 필요한가?

Expected Answer:
사용자가 Graph DB보다 Markdown 노트를 이해하기 쉽기 때문이다.

## Q114
Question:
왜 Bronze Layer가 필요한가?

Expected Answer:
원본 보존, 재추출, 감사 가능성 확보를 위해서다.

## Q115
Question:
왜 Validation Gate가 필요한가?

Expected Answer:
Grounding과 Type Gate를 통해 환각을 줄이기 위해서다.

---

# Category D — Architecture Impact (Q116~Q120)

## Q116
Question:
LightRAG 채택 후 저장 구조는 어떻게 바뀌었지?

Expected Answer:
Gold JSON → LightRAG custom_kg → Memory API 구조로 정리되었다.

## Q117
Question:
Hardware Adaptive가 시스템 전체에 미치는 영향은?

Expected Answer:
RAM 환경별 모델 선택을 자동화한다.

## Q118
Question:
SUPERSEDES가 Memory Engine에 주는 이점은?

Expected Answer:
현재 정책과 과거 정책을 명확히 구분한다.

## Q119
Question:
Timeline 기능이 없으면 어떤 문제가 발생하지?

Expected Answer:
현재 결정과 과거 결정을 구분할 수 없게 된다.

## Q120
Question:
Adaptive Memory Engine의 최종 진화 방향은?

Expected Answer:
Data → Memory → Knowledge → Agent → Action 흐름을 완성하는 Memory OS 코어.

---

# Success Criteria

Multi-Hop Reasoning >= 85%
Cross Document Reasoning >= 85%
Cause & Effect >= 90%
Architecture Impact >= 90%

Part 4 통과 의미:

- 기억한다
- 시간을 기억한다
- 모르면 모른다고 말한다
- 여러 문서를 연결해 추론한다
