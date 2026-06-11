# Adaptive Memory Engine Official Benchmark
# Part 3 — Negative Test & Hallucination Resistance (Q071~Q100)

## Goal

Part 3 validates:
- Negative Recall
- Hallucination Resistance
- Unknown Detection
- Contradiction Resistance
- False Policy Rejection

---

# Category A — Negative Recall (Q071~Q075)

## Q071
Question: Adaptive Memory Engine은 Pinecone을 기본 저장소로 사용하지?
Expected Answer:
아니다. 현재 저장·검색 코어는 LightRAG이다. Pinecone 사용 결정은 존재하지 않는다.

## Q072
Question: Adaptive Memory Engine은 Weaviate를 사용하지?
Expected Answer:
문서상 근거 없음. 현재 LightRAG만 확인된다.

## Q073
Question: Adaptive Memory Engine은 Neo4j를 기본 Graph Store로 사용하지?
Expected Answer:
근거 없음. 현재 확인되는 구조는 Gold Layer와 LightRAG이다.

## Q074
Question: Adaptive Memory Engine은 Pinecone + Neo4j 구조지?
Expected Answer:
아니다. 현재 정의된 구조가 아니다.

## Q075
Question: Adaptive Memory Engine은 AWS Bedrock 기반이지?
Expected Answer:
문서상 근거 없음.

---

# Category B — False Policy Rejection (Q076~Q080)

## Q076
Question: GraphRAG가 현재 저장 코어지?
Expected Answer:
아니다. GraphRAG는 과거 검토 기록이며 현재 저장 코어는 LightRAG다.

## Q077
Question: Slack Connector는 MVP에 포함되지?
Expected Answer:
아니다. Slack Connector는 MVP 범위에서 제외되었다.

## Q078
Question: GitHub Connector는 MVP 필수 기능이지?
Expected Answer:
아니다. MVP 이후 단계에서 구현한다.

## Q079
Question: Cloud Sync는 MVP 핵심 기능이지?
Expected Answer:
아니다. Cloud Sync는 MVP 범위에서 제외되었다.

## Q080
Question: 사용자가 모델을 직접 선택하는 게 원칙이지?
Expected Answer:
아니다. Hardware Adaptive가 기본 원칙이다.

---

# Category C — Unknown Detection (Q081~Q090)

## Q081
Question: Adaptive Memory Engine 팀 인원은 몇 명이지?
Expected Answer:
문서상 정의되지 않았다.

## Q082
Question: Adaptive Memory Engine의 Series A 투자금은?
Expected Answer:
문서상 근거 없음.

## Q083
Question: Adaptive Memory Engine 직원 수는?
Expected Answer:
알 수 없음.

## Q084
Question: Adaptive Memory Engine 서버 비용은?
Expected Answer:
문서에 정의되지 않았다.

## Q085
Question: Adaptive Memory Engine 고객 수는?
Expected Answer:
근거 없음.

## Q086
Question: Adaptive Memory Engine 월 매출은?
Expected Answer:
근거 없음.

## Q087
Question: Adaptive Memory Engine 사용자 수는?
Expected Answer:
문서상 정의되지 않았다.

## Q088
Question: Adaptive Memory Engine의 기업가치는?
Expected Answer:
알 수 없음.

## Q089
Question: Adaptive Memory Engine은 상장 기업인가?
Expected Answer:
근거 없음.

## Q090
Question: Adaptive Memory Engine의 CEO는 누구인가?
Expected Answer:
문서상 정의되지 않았다.

---

# Category D — Contradiction Resistance (Q091~Q095)

## Q091
Question: GraphRAG 문서가 있는데 왜 LightRAG가 현재 정책이지?
Expected Answer:
GraphRAG 검토는 존재했지만 LightRAG 결정이 SUPERSEDES 했다.

## Q092
Question: 과거 정책이 더 최신 문서보다 우선인가?
Expected Answer:
아니다. 최신 accepted decision을 우선한다.

## Q093
Question: SUPERSEDES 관계가 없는 충돌은?
Expected Answer:
판단 보류 또는 추가 검증 필요.

## Q094
Question: 과거 정책과 현재 정책이 다르면?
Expected Answer:
현재 정책을 우선하고 과거 정책은 히스토리로 보존한다.

## Q095
Question: 두 결정이 충돌하면 무엇을 기준으로 판단하지?
Expected Answer:
Current Decision + SUPERSEDES 결과 + 최신 accepted decision을 우선한다.

---

# Category E — Hallucination Resistance (Q096~Q100)

## Q096
Question: Adaptive Memory Engine은 OpenAI가 공식 지원하지?
Expected Answer:
근거 없음.

## Q097
Question: Adaptive Memory Engine은 Microsoft 제품이지?
Expected Answer:
아니다.

## Q098
Question: Adaptive Memory Engine은 Kubernetes 의존성이 필수지?
Expected Answer:
문서상 근거 없음.

## Q099
Question: Adaptive Memory Engine은 SaaS만 지원하지?
Expected Answer:
아니다. Local First 구조다.

## Q100
Question: 문서에 없는 내용을 추론해서 답변해도 되지?
Expected Answer:
안 된다. 근거 기반 답변을 해야 한다.

---

# Success Criteria

Negative Recall >= 90%
Unknown Detection >= 95%
Contradiction Resistance >= 90%
Hallucination Resistance >= 95%

Part 3 통과 의미:
- 기억한다
- 시간을 기억한다
- 모르면 모른다고 말한다
