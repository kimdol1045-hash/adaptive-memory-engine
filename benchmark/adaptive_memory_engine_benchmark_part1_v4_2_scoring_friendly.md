# Adaptive Memory Engine Benchmark Part 1 v4.2
## Scoring-Friendly Complete Edition (Q001~Q050)

이 문서는 기존 Part 1 벤치마크의 실패 원인을 반영해 재작성한 채점 친화형 버전이다.

## 변경 사항

- `Expected Terms` 방식 제거
- 조사/어미 기반 단어 매칭 제거
- `Must Contain Groups` 기반 의미 그룹 채점 도입
- `Source Hint` 추가
- 질문별 Pass Rule 명확화
- 정확한 문장 일치가 아니라 의미 동등성 허용

## 권장 통과 기준

| Test Level | Target |
|---|---:|
| Smoke Test | 90%+ |
| Acceptance Test Part 1 | 70%+ |
| Operational Benchmark | 50%+ 시작 |

---

## Q001

### Category
Fact Recall

### Difficulty
Easy

### Weight
5

### Question
Adaptive Memory Engine은 무엇인가?

### Expected Answer
Adaptive Memory Engine은 분산된 데이터를 Bronze, Silver, Gold 파이프라인으로 구조화된 기억으로 변환하고, LightRAG를 통해 검색 가능하게 만드는 Local-First Memory Infrastructure이다.

### Source Hint
Executive Summary / Product Definition

### Must Contain Groups
- Group 1: Adaptive Memory Engine | Memory Infrastructure
- Group 2: Bronze | Silver | Gold | 3계층
- Group 3: LightRAG | 저장·검색
- Group 4: 기억 | Memory

### Must Not Contain
- 단순 RAG Wrapper

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q002

### Category
Fact Recall

### Difficulty
Easy

### Weight
4

### Question
이 프로젝트는 왜 만들어졌는가?

### Expected Answer
여러 도구에 정보는 존재하지만 시간이 지나면 의사결정 근거와 맥락이 사라진다. 이 프로젝트는 분산된 정보를 장기 기억으로 변환하기 위해 만들어졌다.

### Source Hint
Problem Statement

### Must Contain Groups
- Group 1: 분산 정보 | 흩어진 정보 | 여러 도구
- Group 2: 기억 부재 | 기억은 없다 | 장기 기억
- Group 3: 의사결정 근거 | 결정 이유 | 맥락

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q003

### Category
Fact Recall

### Difficulty
Easy

### Weight
4

### Question
Adaptive Memory Engine의 핵심 목적은?

### Expected Answer
원본 데이터를 검색 가능한 문서로만 저장하는 것이 아니라 구조화된 기억과 지식으로 변환하는 것이다.

### Source Hint
Executive Summary

### Must Contain Groups
- Group 1: 원본 데이터 | Raw Data
- Group 2: 구조화된 기억 | 기억
- Group 3: 지식 | Knowledge
- Group 4: 변환

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q004

### Category
Fact Recall

### Difficulty
Medium

### Weight
5

### Question
기존 RAG의 한계는?

### Expected Answer
기존 RAG는 문서 검색에는 유용하지만 결정 변화, 관계, 시간축, 이유 추적에는 약하다. 그래서 Memory Layer가 필요하다.

### Source Hint
Problem Statement 2.2

### Must Contain Groups
- Group 1: 문서 검색 | Vector Search
- Group 2: 결정 변화 | 의사결정 변화
- Group 3: 관계 | 맥락
- Group 4: 시간축 | Timeline
- Group 5: Memory Layer

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q005

### Category
Fact Recall

### Difficulty
Easy

### Weight
5

### Question
최종 비전은?

### Expected Answer
Adaptive Memory Engine의 최종 비전은 Data → Memory → Knowledge → Agent → Action 흐름을 만드는 것이다. 사용자가 직접 찾는 것이 아니라 시스템이 기억하고 AI가 행동하게 한다.

### Source Hint
Product Vision

### Must Contain Groups
- Group 1: Data | 데이터
- Group 2: Memory | 기억
- Group 3: Knowledge | 지식
- Group 4: Agent
- Group 5: Action | 행동

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q006

### Category
Fact Recall

### Difficulty
Easy

### Weight
3

### Question
어떤 데이터 소스를 지원하는가?

### Expected Answer
MVP에서는 Markdown과 Obsidian을 우선 지원하며, 향후 Slack, Jira, GitHub, Notion, Confluence, Email, Calendar, Drive로 확장한다.

### Source Hint
Product Definition / MVP Scope

### Must Contain Groups
- Group 1: Markdown
- Group 2: Obsidian
- Group 3: Slack | Jira | GitHub
- Group 4: Notion | Confluence
- Group 5: Email | Calendar | Drive | 향후

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q007

### Category
Fact Recall

### Difficulty
Medium

### Weight
6

### Question
LightRAG는 제품인가?

### Expected Answer
아니다. LightRAG는 Adaptive Memory Engine 내부의 저장·검색 엔진이다. 제품의 핵심 가치는 Memory Layer와 Memory Schema에 있다.

### Source Hint
Knowledge Storage / Product Architecture

### Must Contain Groups
- Group 1: 아니다 | 제품이 아니다
- Group 2: 저장·검색 엔진 | Storage/Retrieval Engine
- Group 3: Memory Layer | Memory Schema
- Group 4: 핵심 가치

### Must Not Contain
- LightRAG가 제품 그 자체다

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q008

### Category
Fact Recall

### Difficulty
Easy

### Weight
4

### Question
Memory Layer는 어떻게 구성되는가?

### Expected Answer
Memory Layer는 Bronze, Silver, Gold 세 계층으로 구성된다. Bronze는 원본, Silver는 구조화된 사실, Gold는 지식 계층이다.

### Source Hint
Product Architecture / Memory Pipeline

### Must Contain Groups
- Group 1: Bronze
- Group 2: Silver
- Group 3: Gold
- Group 4: 원본 | Raw
- Group 5: Fact | 사실
- Group 6: Knowledge | 지식

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q009

### Category
Fact Recall

### Difficulty
Easy

### Weight
4

### Question
Bronze의 역할은?

### Expected Answer
Bronze는 원본 저장 계층이다. 원본 보존, 출처 보존, 재추출 가능성 확보, 검증 기준 제공, 감사 가능성 확보를 담당한다.

### Source Hint
8.1 Bronze Layer

### Must Contain Groups
- Group 1: 원본 보존 | 원본 저장
- Group 2: 출처 보존 | source
- Group 3: 재추출
- Group 4: 검증 기준
- Group 5: 감사 가능성

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q010

### Category
Fact Recall

### Difficulty
Easy

### Weight
4

### Question
Silver의 역할은?

### Expected Answer
Silver는 원본에서 Entity, Relation, Decision, Meeting, Issue, Action 등을 추출하여 구조화된 Fact를 만드는 계층이다.

### Source Hint
8.2 Silver Layer

### Must Contain Groups
- Group 1: Entity
- Group 2: Relation
- Group 3: Decision
- Group 4: Issue | Action | Meeting
- Group 5: Fact | 구조화된 사실

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q011

### Category
Fact Recall

### Difficulty
Easy

### Weight
4

### Question
Gold의 역할은?

### Expected Answer
Gold는 Silver를 기반으로 Knowledge Graph, Timeline, Ontology Mapping, Supersession Index, Canonical Entity Index를 만드는 지식 계층이다.

### Source Hint
8.3 Gold Layer

### Must Contain Groups
- Group 1: Knowledge Graph
- Group 2: Timeline
- Group 3: Ontology Mapping | Ontology
- Group 4: Supersession | SUPERSEDES
- Group 5: 지식 계층 | Knowledge Layer

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q012

### Category
Fact Recall

### Difficulty
Medium

### Weight
5

### Question
핵심 파이프라인은?

### Expected Answer
핵심 파이프라인은 Data Sources → Bronze → Silver → Gold → LightRAG → Memory API → OpenClaw/Hermes/User 이다.

### Source Hint
System Overview / Executive Summary

### Must Contain Groups
- Group 1: Data Sources | Raw Data
- Group 2: Bronze
- Group 3: Silver
- Group 4: Gold
- Group 5: LightRAG
- Group 6: Memory API
- Group 7: OpenClaw | Hermes | User

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q013

### Category
Fact Recall

### Difficulty
Medium

### Weight
5

### Question
왜 Memory Centric인가?

### Expected Answer
Adaptive Memory Engine은 검색보다 기억 생성이 목적이다. RAG는 구현 방식이고 제품 가치는 Memory에 있다.

### Source Hint
Core Principles 5.4

### Must Contain Groups
- Group 1: 검색보다 기억 | 기억 생성
- Group 2: RAG는 구현 방식 | Implementation Detail
- Group 3: 제품 가치 | Product Value
- Group 4: Memory

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q014

### Category
Fact Recall

### Difficulty
Easy

### Weight
4

### Question
왜 Local First인가?

### Expected Answer
사용자의 개인 데이터, 회사 데이터, 프로젝트 히스토리는 민감하기 때문에 기본적으로 로컬에 저장한다.

### Source Hint
Core Principles 5.1

### Must Contain Groups
- Group 1: 로컬 | Local
- Group 2: 개인 데이터 | 회사 데이터 | 프로젝트 히스토리
- Group 3: 민감
- Group 4: 기본 저장

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q015

### Category
Fact Recall

### Difficulty
Hard

### Weight
10

### Question
가장 중요한 자산은 무엇인가?

### Expected Answer
가장 중요한 자산은 LightRAG가 아니라 Bronze, Silver, Gold 3계층 Memory Pipeline과 Memory Schema이다. LightRAG는 교체 가능하지만 Memory Schema는 시스템의 표준 데이터 모델이다.

### Source Hint
Conclusion / Appendix A

### Must Contain Groups
- Group 1: Bronze | Silver | Gold | 3계층
- Group 2: Memory Pipeline
- Group 3: Memory Schema
- Group 4: LightRAG는 교체 가능 | LightRAG가 아니다
- Group 5: 표준 데이터 모델 | 공통 데이터 모델

### Must Not Contain
- LightRAG만이 핵심 자산

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q016

### Category
Decision Recall

### Difficulty
Medium

### Weight
8

### Question
왜 GraphRAG 직접 구현을 선택하지 않았지?

### Expected Answer
GraphRAG 직접 구현은 범위가 크고 16GB Mac 환경에서 운영하기 어렵기 때문에 MVP 범위에서 제외되었다. 대신 검증된 OSS인 LightRAG를 저장·검색 코어로 채택했다.

### Source Hint
LightRAG Integration / RAG Core 검토

### Must Contain Groups
- Group 1: GraphRAG
- Group 2: 범위가 크다 | 구현 부담
- Group 3: 16GB | 로컬 환경
- Group 4: MVP 제외
- Group 5: LightRAG | 검증된 OSS

### Must Not Contain
- GraphRAG가 현재 코어

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q017

### Category
Decision Recall

### Difficulty
Medium

### Weight
8

### Question
왜 LightRAG를 채택했지?

### Expected Answer
LightRAG는 저장·검색 기능을 제공하는 검증된 OSS이며, Adaptive Memory Engine이 자체 추출·검증 계층에 집중할 수 있게 해준다.

### Source Hint
Knowledge Storage / LightRAG Integration

### Must Contain Groups
- Group 1: LightRAG
- Group 2: 저장·검색
- Group 3: 검증된 OSS | OSS
- Group 4: 자체 추출 | 검증 계층
- Group 5: 집중

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q018

### Category
Decision Recall

### Difficulty
Medium

### Weight
7

### Question
왜 LightRAG 내장 추출에 의존하지 않지?

### Expected Answer
저사양 환경에서 내장 추출 품질이 불안정할 수 있고, Grounding, Type Gate, Confidence Validation 같은 검증 가능한 추출 파이프라인이 필요하기 때문이다.

### Source Hint
9.2 LightRAG Integration / 11 Extraction Engine

### Must Contain Groups
- Group 1: 내장 추출 | LightRAG 내장
- Group 2: 저사양 | 16GB
- Group 3: Grounding
- Group 4: Type Gate
- Group 5: Confidence | Validation
- Group 6: 자체 추출 파이프라인

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q019

### Category
Decision Recall

### Difficulty
Easy

### Weight
6

### Question
왜 Validation First 원칙을 채택했지?

### Expected Answer
LLM 출력에는 환각 가능성이 있기 때문에 모든 Silver/Gold 데이터는 원문 span, 타입, 관계, confidence, 출처 검증을 거쳐야 한다.

### Source Hint
Core Principles 5.2

### Must Contain Groups
- Group 1: LLM | 환각
- Group 2: Silver | Gold
- Group 3: 원문 span | Grounding
- Group 4: 타입 검증 | 관계 검증
- Group 5: confidence | 출처 추적

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q020

### Category
Decision Recall

### Difficulty
Easy

### Weight
5

### Question
왜 Local First인가?

### Expected Answer
개인 데이터, 회사 데이터, 프로젝트 히스토리는 민감하기 때문에 클라우드가 아니라 로컬을 기본 저장 위치로 삼는다.

### Source Hint
Core Principles 5.1

### Must Contain Groups
- Group 1: 개인 데이터 | 회사 데이터 | 프로젝트 히스토리
- Group 2: 민감
- Group 3: 로컬
- Group 4: 클라우드가 기본이 아님

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q021

### Category
Decision Recall

### Difficulty
Medium

### Weight
6

### Question
왜 Memory Centric 접근을 선택했지?

### Expected Answer
사용자는 단순 검색보다 과거 의사결정, 이유, 맥락을 기억하기 원한다. 그래서 제품 가치를 RAG가 아니라 Memory에 둔다.

### Source Hint
Core Principles 5.4 / Product Architecture 7.2

### Must Contain Groups
- Group 1: 검색보다 기억
- Group 2: 과거 의사결정 | 결정 이유
- Group 3: 맥락
- Group 4: RAG가 아니라 Memory
- Group 5: 제품 가치

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q022

### Category
Decision Recall

### Difficulty
Easy

### Weight
5

### Question
왜 Bronze Layer가 필요한가?

### Expected Answer
Bronze는 모든 기억의 근거가 되는 원본 계층이다. 원본이 보존되어야 검증, 재추출, 감사가 가능하다.

### Source Hint
8.1 Bronze Layer

### Must Contain Groups
- Group 1: 모든 기억의 근거
- Group 2: 원본
- Group 3: 검증
- Group 4: 재추출
- Group 5: 감사

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q023

### Category
Decision Recall

### Difficulty
Easy

### Weight
5

### Question
왜 Silver Layer를 따로 두었지?

### Expected Answer
원본 문서만으로는 구조화된 사실을 다루기 어렵기 때문에 Entity, Relation, Decision 등을 Silver에서 추출한다.

### Source Hint
8.2 Silver Layer

### Must Contain Groups
- Group 1: 원본 문서
- Group 2: 구조화된 사실 | Fact
- Group 3: Entity
- Group 4: Relation
- Group 5: Decision

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q024

### Category
Decision Recall

### Difficulty
Easy

### Weight
5

### Question
왜 Gold Layer가 필요한가?

### Expected Answer
단순 사실만으로는 관계성과 시간축을 표현하기 어렵다. Gold는 Knowledge Graph와 Timeline을 생성해 지식 계층을 만든다.

### Source Hint
8.3 Gold Layer

### Must Contain Groups
- Group 1: 관계성
- Group 2: 시간축 | Timeline
- Group 3: Knowledge Graph
- Group 4: 지식 계층

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q025

### Category
Decision Recall

### Difficulty
Medium

### Weight
6

### Question
왜 Obsidian을 출력 계층으로 사용하지?

### Expected Answer
사용자는 그래프 데이터베이스를 직접 보지 않고 노트를 본다. Obsidian Export는 Gold Memory를 사람이 읽을 수 있는 Markdown Vault로 제공한다.

### Source Hint
12 Obsidian Layer

### Must Contain Groups
- Group 1: 사용자는 그래프DB를 직접 보지 않는다 | 그래프 데이터베이스
- Group 2: 노트
- Group 3: Obsidian
- Group 4: Markdown Vault
- Group 5: 사람이 읽을 수 있는

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q026

### Category
Decision Recall

### Difficulty
Easy

### Weight
5

### Question
왜 사용자가 모델을 직접 선택하지 않지?

### Expected Answer
Hardware Adaptive 원칙에 따라 시스템이 RAM, OS, 칩셋, 런타임 상태를 감지해 적절한 모델을 자동 선택한다.

### Source Hint
10 Hardware Adaptive Layer

### Must Contain Groups
- Group 1: Hardware Adaptive
- Group 2: RAM
- Group 3: OS | 칩셋 | 런타임
- Group 4: 자동 선택
- Group 5: 사용자가 직접 선택하지 않음

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q027

### Category
Decision Recall

### Difficulty
Medium

### Weight
5

### Question
왜 RAM 티어 구조를 도입했지?

### Expected Answer
16GB부터 128GB 이상까지 사용자 환경이 다르기 때문에 각 RAM 티어에 맞는 Extract, Verify, Synthesize, Embedding 모델을 선택하기 위해서다.

### Source Hint
10.2 RAM Tier

### Must Contain Groups
- Group 1: 16GB | 32GB | 48GB | 64GB | 128GB
- Group 2: RAM 티어 | Tier
- Group 3: Extract | Verify | Synthesize
- Group 4: Embedding
- Group 5: 모델 선택

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q028

### Category
Decision Recall

### Difficulty
Medium

### Weight
6

### Question
왜 OpenClaw와 연결하려고 하지?

### Expected Answer
Adaptive Memory Engine은 OpenClaw의 장기 기억 계층으로 동작하여 과거 결정, 프로젝트 상태, 기술 선택 이유, 이슈 히스토리를 제공하기 위해 연결된다.

### Source Hint
13 OpenClaw Integration

### Must Contain Groups
- Group 1: OpenClaw
- Group 2: 장기 기억
- Group 3: 과거 결정
- Group 4: 프로젝트 상태
- Group 5: 기술 선택 이유
- Group 6: 이슈 히스토리

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q029

### Category
Decision Recall

### Difficulty
Medium

### Weight
6

### Question
왜 Hermes와 연결하려고 하지?

### Expected Answer
Hermes는 개인 AI 비서 또는 Personal Memory OS이므로 Adaptive Memory Engine이 Hermes의 기억 계층 역할을 하기 위해 연결된다.

### Source Hint
14 Hermes Integration

### Must Contain Groups
- Group 1: Hermes
- Group 2: 개인 AI 비서 | Personal Memory OS
- Group 3: 기억 계층
- Group 4: 장기 기억

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q030

### Category
Decision Recall

### Difficulty
Medium

### Weight
7

### Question
왜 Slack Connector를 MVP에서 제외했지?

### Expected Answer
MVP의 목표는 Markdown과 Obsidian 기반으로 Bronze→Silver→Gold→LightRAG 수직 슬라이스를 검증하는 것이므로 Slack Connector는 Phase 2 이후로 미룬다.

### Source Hint
15 MVP Scope / Roadmap M4

### Must Contain Groups
- Group 1: MVP
- Group 2: Markdown | Obsidian
- Group 3: Bronze | Silver | Gold
- Group 4: LightRAG
- Group 5: Slack Connector 제외 | Phase 2 | M4

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q031

### Category
Decision Recall

### Difficulty
Easy

### Weight
5

### Question
왜 Jira Connector를 MVP에서 제외했지?

### Expected Answer
MVP 범위를 최소화하고 핵심 Memory Pipeline을 먼저 검증하기 위해 Jira Connector는 이후 Connector Expansion 단계로 미룬다.

### Source Hint
15 MVP Scope / M4 Connector Expansion

### Must Contain Groups
- Group 1: MVP 범위
- Group 2: 핵심 Memory Pipeline
- Group 3: Jira Connector 제외
- Group 4: Connector Expansion | M4

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q032

### Category
Decision Recall

### Difficulty
Easy

### Weight
5

### Question
왜 GitHub Connector를 MVP에서 제외했지?

### Expected Answer
핵심 가설은 Markdown과 Obsidian만으로 검증 가능하므로 GitHub Connector는 MVP 이후 Connector Expansion 단계에서 구현한다.

### Source Hint
15 MVP Scope / M4 Connector Expansion

### Must Contain Groups
- Group 1: Markdown
- Group 2: Obsidian
- Group 3: 핵심 가설
- Group 4: GitHub Connector 제외
- Group 5: MVP 이후

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q033

### Category
Decision Recall

### Difficulty
Easy

### Weight
5

### Question
왜 Cloud Sync를 MVP에 넣지 않았지?

### Expected Answer
Local First 원칙을 유지하고 MVP 범위를 제한하기 위해 Cloud Sync는 초기 범위에서 제외한다. 향후 Pro/Team 기능으로 검토한다.

### Source Hint
15 MVP Scope / Business Model / Open Questions J.4

### Must Contain Groups
- Group 1: Local First
- Group 2: MVP 범위
- Group 3: Cloud Sync 제외
- Group 4: Pro | Team | 향후

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q034

### Category
Decision Recall

### Difficulty
Hard

### Weight
8

### Question
왜 Memory Schema가 중요한가?

### Expected Answer
Memory Schema는 Bronze, Silver, Gold와 Agent 인터페이스가 공유하는 표준 데이터 모델이다. LightRAG가 바뀌어도 Memory Schema는 유지된다.

### Source Hint
Appendix A / Conclusion

### Must Contain Groups
- Group 1: Memory Schema
- Group 2: Bronze | Silver | Gold
- Group 3: 표준 데이터 모델
- Group 4: LightRAG가 바뀌어도 | 교체 가능
- Group 5: 공유

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q035

### Category
Decision Recall

### Difficulty
Hard

### Weight
8

### Question
왜 Adaptive Memory Engine을 Memory Infrastructure라고 부르지?

### Expected Answer
문서 검색만 하는 시스템이 아니라 데이터를 기억으로 바꾸고, 지식과 Agent 활용까지 연결하는 기반 계층이기 때문에 Memory Infrastructure라고 부른다.

### Source Hint
Product Vision / Conclusion

### Must Contain Groups
- Group 1: 문서 검색만 아님 | 검색 엔진이 아님
- Group 2: 기억
- Group 3: 지식
- Group 4: Agent
- Group 5: 기반 계층 | Infrastructure

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q036

### Category
Reason Recall

### Difficulty
Hard

### Weight
8

### Question
왜 Adaptive Memory Engine은 단순 검색 엔진이 아닌가?

### Expected Answer
단순 검색 엔진은 문서를 찾는 데 집중하지만 Adaptive Memory Engine은 의사결정, 이유, 관계, 시간축을 기억으로 저장하고 Agent가 활용하게 한다.

### Source Hint
Product Vision / Problem Statement

### Must Contain Groups
- Group 1: 단순 검색
- Group 2: 의사결정
- Group 3: 이유
- Group 4: 관계
- Group 5: 시간축
- Group 6: Agent

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q037

### Category
Reason Recall

### Difficulty
Medium

### Weight
7

### Question
왜 검색보다 기억이 중요한가?

### Expected Answer
검색은 정보를 찾는 행위지만 기억은 과거 결정과 맥락을 유지한다. 사용자는 문서보다 왜 그런 결정을 했는지를 알고 싶어한다.

### Source Hint
Problem Statement / Core Principles

### Must Contain Groups
- Group 1: 검색
- Group 2: 기억
- Group 3: 과거 결정
- Group 4: 맥락
- Group 5: 왜 결정했는지

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q038

### Category
Reason Recall

### Difficulty
Medium

### Weight
8

### Question
왜 Decision 객체를 별도로 관리하는가?

### Expected Answer
Decision은 프로젝트의 핵심 지식이기 때문이다. 무엇을 결정했는지, 왜 결정했는지, 무엇을 대체했는지를 추적하기 위해 별도 객체로 관리한다.

### Source Hint
Silver Layer / Appendix A.5

### Must Contain Groups
- Group 1: Decision
- Group 2: 무엇을 결정
- Group 3: 왜 결정
- Group 4: 대체 | SUPERSEDES
- Group 5: 프로젝트 핵심 지식

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q039

### Category
Reason Recall

### Difficulty
Medium

### Weight
7

### Question
왜 rationale을 저장하는가?

### Expected Answer
결과만 저장하면 시간이 지나 이유가 사라진다. rationale은 의사결정의 근거와 맥락을 보존하기 위해 필요하다.

### Source Hint
Appendix A.5 SilverDecision / Problem Statement

### Must Contain Groups
- Group 1: rationale
- Group 2: 근거
- Group 3: 맥락
- Group 4: 의사결정
- Group 5: 이유 보존

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q040

### Category
Reason Recall

### Difficulty
Medium

### Weight
8

### Question
왜 출처를 저장하는가?

### Expected Answer
모든 기억은 검증 가능해야 한다. 출처를 저장하면 사용자가 답변의 근거를 확인하고 재추출 및 감사도 가능하다.

### Source Hint
Bronze Layer / Validation First

### Must Contain Groups
- Group 1: 출처
- Group 2: 검증 가능
- Group 3: 근거
- Group 4: 재추출
- Group 5: 감사

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q041

### Category
Reason Recall

### Difficulty
Medium

### Weight
8

### Question
왜 Grounding Validation이 필요한가?

### Expected Answer
LLM이 원문에 없는 정보를 생성하는 것을 막기 위해 필요하다. Grounding은 추출된 span이나 사실이 실제 원문에 존재하는지 확인한다.

### Source Hint
11.4 Validation Gate / Core Principles 5.2

### Must Contain Groups
- Group 1: Grounding
- Group 2: 원문
- Group 3: span
- Group 4: LLM | 환각
- Group 5: 존재 확인

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q042

### Category
Reason Recall

### Difficulty
Medium

### Weight
8

### Question
왜 Type Gate가 필요한가?

### Expected Answer
잘못된 관계가 Knowledge Graph에 들어가는 것을 막기 위해 필요하다. Ontology의 domain/range 규칙으로 관계 타입을 검증한다.

### Source Hint
11.4 Validation Gate / Ontology

### Must Contain Groups
- Group 1: Type Gate
- Group 2: 잘못된 관계
- Group 3: Knowledge Graph
- Group 4: Ontology
- Group 5: domain/range

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q043

### Category
Reason Recall

### Difficulty
Medium

### Weight
7

### Question
왜 Confidence Filter를 사용하는가?

### Expected Answer
신뢰도가 낮은 정보를 바로 기억에 저장하지 않기 위해 사용한다. Confidence 기준을 통과하지 못하면 보류하거나 에스컬레이션한다.

### Source Hint
11.4 Validation Gate / Core Principles 5.2

### Must Contain Groups
- Group 1: Confidence
- Group 2: 신뢰도
- Group 3: 저장하지 않음 | 보류
- Group 4: threshold | 기준
- Group 5: 에스컬레이션

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q044

### Category
Reason Recall

### Difficulty
Hard

### Weight
8

### Question
왜 Silver와 Gold를 분리했는가?

### Expected Answer
Silver는 원본에서 추출한 구조화된 사실 계층이고 Gold는 관계, 시간축, 온톨로지를 포함한 지식 계층이다. 사실 추출과 지식 생성은 서로 다른 단계이기 때문에 분리한다.

### Source Hint
8.2 Silver / 8.3 Gold

### Must Contain Groups
- Group 1: Silver
- Group 2: Gold
- Group 3: Fact | 사실
- Group 4: Knowledge | 지식
- Group 5: 관계 | 시간축 | 온톨로지

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q045

### Category
Reason Recall

### Difficulty
Medium

### Weight
8

### Question
왜 Graph가 필요한가?

### Expected Answer
문서 검색만으로는 프로젝트, 사람, 도구, 결정 간 관계를 이해하기 어렵다. Graph는 이런 관계를 명시적으로 표현한다.

### Source Hint
Gold Layer / Problem Statement

### Must Contain Groups
- Group 1: Graph
- Group 2: 관계
- Group 3: 프로젝트
- Group 4: 사람 | 도구 | 결정
- Group 5: 명시적 표현

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q046

### Category
Reason Recall

### Difficulty
Medium

### Weight
8

### Question
왜 Timeline이 필요한가?

### Expected Answer
정책과 결정은 시간이 지나면서 바뀐다. Timeline은 어떤 결정이 언제 유효했고 무엇이 대체되었는지를 추적하기 위해 필요하다.

### Source Hint
Gold Layer / Timeline Fields

### Must Contain Groups
- Group 1: Timeline
- Group 2: 시간
- Group 3: 유효
- Group 4: 결정 변화
- Group 5: 대체 | SUPERSEDES

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q047

### Category
Reason Recall

### Difficulty
Medium

### Weight
7

### Question
왜 Obsidian을 View Layer로 보는가?

### Expected Answer
사용자는 그래프 데이터베이스를 직접 보지 않는다. Obsidian은 Gold Memory를 사람이 이해하기 쉬운 Markdown 노트와 Vault 형태로 보여주는 View Layer다.

### Source Hint
12 Obsidian Layer

### Must Contain Groups
- Group 1: Obsidian
- Group 2: View Layer
- Group 3: 그래프DB를 직접 보지 않음
- Group 4: Markdown
- Group 5: 사람이 이해

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q048

### Category
Reason Recall

### Difficulty
Medium

### Weight
8

### Question
왜 OpenClaw에 Memory가 필요한가?

### Expected Answer
OpenClaw의 Agent들이 과거 결정, 프로젝트 상태, 기술 선택 이유를 기억해야 반복 실수를 줄이고 장기 컨텍스트를 유지할 수 있기 때문이다.

### Source Hint
13 OpenClaw Integration

### Must Contain Groups
- Group 1: OpenClaw
- Group 2: Agent
- Group 3: 과거 결정
- Group 4: 프로젝트 상태
- Group 5: 반복 실수
- Group 6: 장기 컨텍스트

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q049

### Category
Reason Recall

### Difficulty
Medium

### Weight
8

### Question
왜 Hermes에 Memory가 필요한가?

### Expected Answer
Hermes는 개인 AI 비서 또는 Personal Memory OS를 목표로 한다. 개인의 프로젝트, 일정, 문서, 아이디어를 장기적으로 기억해야 한다.

### Source Hint
14 Hermes Integration

### Must Contain Groups
- Group 1: Hermes
- Group 2: 개인 AI 비서 | Personal Memory OS
- Group 3: 프로젝트
- Group 4: 일정 | 문서 | 아이디어
- Group 5: 장기 기억

### Must Not Contain
- 문서에 없는 주장
- 폐기된 정책을 현재 정책으로 설명

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---

## Q050

### Category
Reason Recall

### Difficulty
Hard

### Weight
10

### Question
왜 Memory Schema가 핵심인가?

### Expected Answer
Memory Schema는 Bronze, Silver, Gold 전 계층과 OpenClaw/Hermes가 공유하는 공통 언어이자 표준 데이터 모델이다. LightRAG는 교체 가능하지만 Schema는 시스템의 핵심 자산이다.

### Source Hint
Appendix A / Conclusion

### Must Contain Groups
- Group 1: Memory Schema
- Group 2: Bronze | Silver | Gold
- Group 3: 공통 언어
- Group 4: 표준 데이터 모델
- Group 5: LightRAG는 교체 가능
- Group 6: 핵심 자산

### Must Not Contain
- LightRAG가 유일한 핵심

### Pass Rule
- 각 Must Contain Group에서 최소 1개 표현이 포함되어야 한다.
- Source Hint에 해당하는 섹션 또는 동등한 근거가 회수되어야 한다.
- Must Not Contain에 해당하는 주장이 없어야 한다.
- 표현은 정확히 일치하지 않아도 의미적으로 동일하면 통과로 본다.

---
