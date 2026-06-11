# Adaptive Memory Engine Official Benchmark
# Part 5 — Agent Memory & Memory OS Foundation (Q121~Q150)

## Goal

Part 5 validates whether Adaptive Memory Engine can be used as a practical Memory OS foundation by agents such as OpenClaw and Hermes.

검증 대상:
- Memory Diff
- Memory Query Language (MQL)
- Explainable Answer
- Agent Memory API
- Personal Memory Layer
- OpenClaw Agent Use Case
- Hermes Personal Memory Use Case
- Long-Term Regression Readiness

---

# Category A — Memory Diff Engine (Q121~Q126)

## Q121
### Question
지난 7일 동안 어떤 결정이 바뀌었지?

### Expected Answer
최근 7일 기준으로 새로 accepted 된 decision, SUPERSEDES 된 decision, current=false가 된 과거 decision을 구분해서 보여줘야 한다.

### Must Contain
- 최근 7일
- accepted decision
- SUPERSEDES
- current=false
- 변경된 decision

### Must Not Contain
- 모든 과거 decision을 현재 decision처럼 설명

---

## Q122
### Question
지난주 대비 현재 저장 정책은 어떻게 바뀌었지?

### Expected Answer
초기 JSON-only 저장 정책은 과거 정책으로 남고, 현재는 Gold JSON을 LightRAG custom_kg로 변환해 사용하는 정책이 current=true로 유지된다.

### Must Contain
- JSON-only
- LightRAG custom_kg
- current=true
- current=false

---

## Q123
### Question
새로 추가된 Memory 관련 결정만 보여줘.

### Expected Answer
기존 knowledge 전체가 아니라 새롭게 추가된 decision 또는 accepted decision만 필터링해서 반환해야 한다.

### Must Contain
- 새로 추가
- decision
- accepted
- filter

---

## Q124
### Question
이번 스프린트에서 변경된 architecture decision은?

### Expected Answer
스프린트 기간 내 변경된 architecture decision을 Timeline 기준으로 찾아야 하며, 변경 전/후 관계가 있으면 SUPERSEDES 관계도 함께 보여줘야 한다.

### Must Contain
- sprint
- architecture decision
- Timeline
- SUPERSEDES

---

## Q125
### Question
어떤 결정이 현재 상태를 바꾸었지?

### Expected Answer
현재 상태에 영향을 준 accepted decision을 원인으로 추적하고, 대체된 과거 decision이 있다면 함께 설명해야 한다.

### Must Contain
- accepted decision
- 현재 상태
- 원인
- 대체된 decision

---

## Q126
### Question
Memory Diff가 필요한 이유는?

### Expected Answer
Memory Diff는 사용자가 전체 문서를 다시 읽지 않고도 특정 기간 동안 무엇이 바뀌었는지, 어떤 결정이 새로 생겼는지, 어떤 정책이 대체되었는지 확인하기 위해 필요하다.

### Must Contain
- 변경점
- 기간
- 새 decision
- 대체된 정책

---

# Category B — Memory Query Language / MQL (Q127~Q132)

## Q127
### Question
current=true인 decision만 조회하려면 어떻게 해야 하지?

### Expected Answer
MQL 또는 Agent API에서 current=true 조건으로 accepted decision만 조회해야 한다.

예:
FIND decisions WHERE current=true

### Must Contain
- current=true
- accepted decision
- FIND decisions

---

## Q128
### Question
LightRAG 결정의 rationale만 조회하려면?

### Expected Answer
decision=LightRAG에 연결된 rationale memory를 조회해야 한다.

예:
WHY decision="LightRAG"

### Must Contain
- LightRAG
- rationale
- WHY

---

## Q129
### Question
특정 프로젝트의 timeline을 보려면?

### Expected Answer
project 또는 corpus 기준으로 timeline query를 실행해야 한다.

예:
SHOW timeline FOR project="Adaptive Memory Engine"

### Must Contain
- SHOW timeline
- project
- Adaptive Memory Engine

---

## Q130
### Question
MQL이 필요한 이유는?

### Expected Answer
자연어 질의만으로는 agent가 안정적으로 memory를 재사용하기 어렵기 때문에, decision/current/rationale/timeline/diff를 구조화된 방식으로 조회하기 위해 MQL이 필요하다.

### Must Contain
- agent
- 구조화된 질의
- decision
- timeline
- diff

---

## Q131
### Question
OpenClaw Agent가 현재 결정만 사용하게 하려면?

### Expected Answer
OpenClaw Agent는 memory.current_decision() 또는 FIND decisions WHERE current=true 같은 API/MQL을 사용해야 한다.

### Must Contain
- OpenClaw
- current decision
- memory.current_decision
- current=true

---

## Q132
### Question
MQL과 자연어 질의는 어떤 관계인가?

### Expected Answer
자연어 질의는 사람이 사용하기 좋고, MQL은 Agent가 안정적으로 사용하기 좋은 구조화된 질의 계층이다. 둘은 병행되어야 한다.

### Must Contain
- 자연어
- MQL
- Agent
- 구조화된 질의

---

# Category C — Explainable Answer (Q133~Q138)

## Q133
### Question
왜 이 답변이 나왔는지 설명할 수 있어야 하나?

### Expected Answer
Memory 시스템은 답변뿐 아니라 어떤 source, decision chain, confidence, reasoning depth를 기반으로 답했는지 설명할 수 있어야 한다.

### Must Contain
- source
- decision chain
- confidence
- reasoning depth

---

## Q134
### Question
Explainable Answer에는 무엇이 포함되어야 하지?

### Expected Answer
answer, sources, confidence, reasoning_depth, decision_chain, currentness 판단, missing evidence 여부가 포함되어야 한다.

### Must Contain
- answer
- sources
- confidence
- reasoning_depth
- decision_chain
- missing evidence

---

## Q135
### Question
LightRAG가 현재 코어라는 답변을 설명해줘.

### Expected Answer
현재 코어는 LightRAG이며, 근거는 LightRAG 도입 결정이다. GraphRAG 검토는 SUPERSEDES 되어 current=false가 되었고, 따라서 현재 결정에서 제외된다.

### Must Contain
- LightRAG
- GraphRAG
- SUPERSEDES
- current=false
- source

---

## Q136
### Question
근거가 부족한 답변은 어떻게 표시해야 하지?

### Expected Answer
근거가 부족하면 confidence를 낮추고, missing evidence 또는 근거 없음으로 표시해야 한다. 추론으로 확정 답변을 만들면 안 된다.

### Must Contain
- confidence
- missing evidence
- 근거 없음
- 확정 답변 금지

---

## Q137
### Question
confidence score는 왜 필요한가?

### Expected Answer
confidence score는 답변의 근거 강도, source 수, decision chain 완성도, reasoning depth를 반영하여 사용자가 신뢰도를 판단할 수 있게 한다.

### Must Contain
- 근거 강도
- source
- decision chain
- reasoning depth
- 신뢰도

---

## Q138
### Question
Explainable Answer가 없으면 어떤 문제가 생기지?

### Expected Answer
답변이 맞더라도 왜 맞는지 검증하기 어렵고, agent가 잘못된 memory를 사용했을 때 디버깅이 어려워진다.

### Must Contain
- 검증 어려움
- 디버깅 어려움
- 잘못된 memory

---

# Category D — Agent Memory API (Q139~Q144)

## Q139
### Question
OpenClaw Agent가 사용해야 할 핵심 Memory API는?

### Expected Answer
memory.search(), memory.current_decision(), memory.timeline(), memory.why(), memory.diff()가 핵심 API이다.

### Must Contain
- memory.search
- memory.current_decision
- memory.timeline
- memory.why
- memory.diff

---

## Q140
### Question
memory.why()는 어떤 역할인가?

### Expected Answer
특정 decision이나 policy의 rationale, source, decision chain을 반환한다.

### Must Contain
- rationale
- source
- decision chain

---

## Q141
### Question
memory.diff()는 어떤 역할인가?

### Expected Answer
특정 기간 동안 변경된 decision, policy, architecture, currentness 변화를 반환한다.

### Must Contain
- 기간
- 변경된 decision
- policy
- currentness

---

## Q142
### Question
memory.timeline()은 어떤 역할인가?

### Expected Answer
decision이나 project의 시간순 변화, accepted/replaced/superseded 상태를 보여준다.

### Must Contain
- 시간순
- accepted
- replaced
- superseded

---

## Q143
### Question
OpenClaw CTO Agent가 Memory를 사용한다면 어떤 순서가 적절한가?

### Expected Answer
현재 decision 조회 → 관련 rationale 조회 → timeline 확인 → 최근 diff 확인 → task/action 결정 순서가 적절하다.

### Must Contain
- current decision
- rationale
- timeline
- diff
- action

---

## Q144
### Question
Agent Memory API가 없으면 어떤 문제가 있지?

### Expected Answer
Agent가 자연어 검색 결과에 의존하게 되어 current decision, rationale, timeline, diff를 안정적으로 재사용하기 어렵다.

### Must Contain
- Agent
- 자연어 검색 의존
- current decision
- rationale
- timeline
- diff

---

# Category E — Personal Memory Layer / Hermes (Q145~Q150)

## Q145
### Question
Hermes에서 필요한 Personal Memory Type은?

### Expected Answer
Email, Calendar, Meeting, Task, Document, Decision, Contact, Project memory가 필요하다.

### Must Contain
- Email
- Calendar
- Meeting
- Task
- Document
- Decision
- Contact
- Project

---

## Q146
### Question
Hermes가 “지난주 왜 이 결정을 했지?”에 답하려면 무엇이 필요하지?

### Expected Answer
지난주 timeline, decision, rationale, source, 관련 meeting/document memory를 연결해야 한다.

### Must Contain
- 지난주
- timeline
- decision
- rationale
- source
- meeting
- document

---

## Q147
### Question
Hermes가 “이번 주 우선순위는?”에 답하려면?

### Expected Answer
Calendar, Task, Project, Decision, 최근 diff를 연결해 이번 주 실행해야 할 우선순위를 추론해야 한다.

### Must Contain
- Calendar
- Task
- Project
- Decision
- diff
- 우선순위

---

## Q148
### Question
Personal Memory Layer가 기존 PRD Memory와 다른 점은?

### Expected Answer
PRD Memory는 제품/결정/아키텍처 중심이고, Personal Memory는 일정, 이메일, 회의, 작업, 사람, 문서 등 개인 맥락 중심이다.

### Must Contain
- PRD Memory
- Personal Memory
- 일정
- 이메일
- 회의
- 작업
- 사람

---

## Q149
### Question
Hermes Memory에서 privacy가 중요한 이유는?

### Expected Answer
개인 일정, 이메일, 연락처, 문서 등 민감한 데이터가 포함되므로 Local First와 권한 기반 접근 제어가 필요하다.

### Must Contain
- privacy
- 개인 일정
- 이메일
- 연락처
- Local First
- 권한

---

## Q150
### Question
Part5를 통과하면 Adaptive Memory Engine은 어떤 단계로 볼 수 있나?

### Expected Answer
Part5를 통과하면 Adaptive Memory Engine은 단순 Memory Engine을 넘어 Agent가 사용할 수 있는 Memory OS Foundation 단계로 볼 수 있다.

### Must Contain
- Memory Engine
- Agent
- Memory OS Foundation
- OpenClaw
- Hermes

---

# Success Criteria

| Area | Target |
|---|---:|
| Memory Diff | >= 85% |
| MQL | >= 85% |
| Explainable Answer | >= 90% |
| Agent Memory API | >= 90% |
| Personal Memory Layer | >= 80% |

## Part 5 Pass Meaning

Part 5 통과 시 Adaptive Memory Engine은 다음 능력을 갖춘 것으로 본다.

- 기억한다
- 시간을 기억한다
- 모르면 모른다고 말한다
- 여러 문서를 연결해 추론한다
- Agent가 사용할 수 있는 Memory OS Foundation이 된다
