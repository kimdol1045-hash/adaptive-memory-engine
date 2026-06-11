# Adaptive Memory Engine Official Benchmark v4.1
# Part 1-A Complete Edition (Q001~Q015)

## Q001
Question: Adaptive Memory Engine은 무엇인가?
Expected Answer:
Adaptive Memory Engine은 분산된 데이터를 Bronze, Silver, Gold 파이프라인으로 기억화하고 LightRAG를 통해 검색 가능하게 만드는 Local-First Memory Infrastructure이다.
Required Sources:
- Executive Summary
- Product Definition
Must Contain:
- Bronze
- Silver
- Gold
- Memory
- LightRAG
Must Not Contain:
- 단순 RAG Wrapper
Weight: 5
Difficulty: Easy
Pass Rule:
Must Contain 4개 이상 포함

---

## Q002
Question: 이 프로젝트는 왜 만들어졌는가?
Expected Answer:
검색은 가능하지만 기억은 없는 문제를 해결하기 위해 만들어졌다. 분산된 정보와 의사결정 근거 손실 문제를 해결한다.
Required Sources:
- Problem Statement
Weight: 4
Difficulty: Easy

---

## Q003
Question: Adaptive Memory Engine의 핵심 목적은?
Expected Answer:
원본 데이터를 구조화된 기억과 지식으로 변환하는 것이다.
Required Sources:
- Executive Summary
Weight: 4

---

## Q004
Question: 기존 RAG의 한계는?
Expected Answer:
문서 검색에는 강하지만 시간축, 의사결정 변화, 관계성, 이유 추적에는 약하다.
Required Sources:
- Problem Statement 2.2
Weight: 5

---

## Q005
Question: 최종 비전은?
Expected Answer:
Data → Memory → Knowledge → Agent → Action 흐름을 만드는 것이다.
Required Sources:
- Product Vision
Weight: 5

---

## Q006
Question: 어떤 데이터 소스를 지원하는가?
Expected Answer:
Markdown, Obsidian, Slack, Jira, GitHub, Notion, Confluence를 지원 대상으로 정의한다.
Required Sources:
- Product Definition
Weight: 3

---

## Q007
Question: LightRAG는 제품인가?
Expected Answer:
아니다. 저장·검색 엔진이며 핵심 가치는 Memory Layer에 있다.
Required Sources:
- Product Architecture
Weight: 6

---

## Q008
Question: Memory Layer는 어떻게 구성되는가?
Expected Answer:
Bronze, Silver, Gold 세 계층으로 구성된다.
Required Sources:
- Product Architecture
Weight: 4

---

## Q009
Question: Bronze의 역할은?
Expected Answer:
원본 데이터 보존, 출처 보존, 재추출 가능성 확보.
Required Sources:
- Bronze Layer
Weight: 4

---

## Q010
Question: Silver의 역할은?
Expected Answer:
Entity, Relation, Decision 등을 추출하여 구조화된 Fact를 생성한다.
Required Sources:
- Silver Layer
Weight: 4

---

## Q011
Question: Gold의 역할은?
Expected Answer:
Knowledge Graph, Timeline, Ontology Mapping을 생성한다.
Required Sources:
- Gold Layer
Weight: 4

---

## Q012
Question: 핵심 파이프라인은?
Expected Answer:
Data Sources → Bronze → Silver → Gold → LightRAG → Memory API → OpenClaw/Hermes.
Required Sources:
- System Overview
Weight: 5

---

## Q013
Question: 왜 Memory Centric인가?
Expected Answer:
검색보다 기억 생성이 중요하기 때문이다. RAG는 구현 방식이고 가치는 Memory에 있다.
Required Sources:
- Core Principles
Weight: 5

---

## Q014
Question: 왜 Local First인가?
Expected Answer:
민감한 데이터를 사용자 로컬에 보존하기 위해서다.
Required Sources:
- Core Principles
Weight: 4

---

## Q015
Question: 가장 중요한 자산은 무엇인가?
Expected Answer:
Bronze/Silver/Gold Memory Pipeline과 Memory Schema이다. LightRAG는 교체 가능하지만 Memory Schema는 시스템의 공통 데이터 모델이다.
Required Sources:
- Conclusion
- Memory Schema
Must Contain:
- Bronze
- Silver
- Gold
- Memory Schema
Weight: 10
Difficulty: Hard
