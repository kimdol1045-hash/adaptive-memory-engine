# Adaptive Memory Engine Official Benchmark v4.2
# Part 1-B Complete Edition (Q016~Q035)

## Q016
Question: 왜 GraphRAG 직접 구현을 선택하지 않았지?
Expected Answer:
GraphRAG 직접 구현은 범위가 크고 16GB 환경 대응이 어려워 MVP 범위에서 제외되었다. 대신 LightRAG를 저장·검색 코어로 채택했다.
Weight: 8

## Q017
Question: 왜 LightRAG를 채택했지?
Expected Answer:
저장·검색 기능을 안정적으로 제공하며 로컬 환경에서 활용 가능한 검증된 OSS이기 때문이다.
Weight: 8

## Q018
Question: 왜 LightRAG 내장 추출에 의존하지 않지?
Expected Answer:
Grounding, Type Gate, Confidence Validation이 가능한 자체 추출 파이프라인을 유지하기 위해서다.
Weight: 7

## Q019
Question: 왜 Validation First 원칙을 채택했지?
Expected Answer:
LLM 환각을 줄이고 검증된 사실만 기억에 저장하기 위해서다.

## Q020
Question: 왜 Local First인가?
Expected Answer:
민감한 데이터와 프로젝트 히스토리를 사용자 로컬에 보존하기 위해서다.

## Q021
Question: 왜 Memory Centric 접근을 선택했지?
Expected Answer:
사용자는 검색보다 의사결정과 맥락을 기억하기 원하기 때문이다.

## Q022
Question: 왜 Bronze Layer가 필요한가?
Expected Answer:
원본 보존, 검증, 재추출의 근거가 되기 때문이다.

## Q023
Question: 왜 Silver Layer를 따로 두었지?
Expected Answer:
구조화된 Fact(Entity, Relation, Decision)를 만들기 위해서다.

## Q024
Question: 왜 Gold Layer가 필요한가?
Expected Answer:
Knowledge Graph와 Timeline을 생성하기 위해서다.

## Q025
Question: 왜 Obsidian을 출력 계층으로 사용하지?
Expected Answer:
사용자는 그래프DB보다 Markdown 노트를 더 쉽게 이해하기 때문이다.

## Q026
Question: 왜 사용자가 모델을 직접 선택하지 않지?
Expected Answer:
Hardware Adaptive 원칙에 따라 자동 선택하기 때문이다.

## Q027
Question: 왜 RAM 티어 구조를 도입했지?
Expected Answer:
다양한 하드웨어 환경에 최적화된 모델을 제공하기 위해서다.

## Q028
Question: 왜 OpenClaw와 연결하려고 하지?
Expected Answer:
OpenClaw의 장기 기억 계층 역할을 수행하기 위해서다.

## Q029
Question: 왜 Hermes와 연결하려고 하지?
Expected Answer:
Hermes의 Personal Memory OS를 지원하기 위해서다.

## Q030
Question: 왜 Slack Connector를 MVP에서 제외했지?
Expected Answer:
핵심 Memory Pipeline 검증에 집중하기 위해서다.

## Q031
Question: 왜 Jira Connector를 MVP에서 제외했지?
Expected Answer:
MVP 범위를 최소화하기 위해서다.

## Q032
Question: 왜 GitHub Connector를 MVP에서 제외했지?
Expected Answer:
Markdown과 Obsidian만으로 핵심 가설 검증이 가능하기 때문이다.

## Q033
Question: 왜 Cloud Sync를 MVP에 넣지 않았지?
Expected Answer:
Local First 원칙과 범위 제한 때문이다.

## Q034
Question: 왜 Memory Schema가 중요한가?
Expected Answer:
모든 계층이 공유하는 표준 데이터 모델이기 때문이다.

## Q035
Question: 왜 Memory Infrastructure라고 부르지?
Expected Answer:
검색이 아니라 기억, 지식, Agent 활용까지 포함하기 때문이다.
