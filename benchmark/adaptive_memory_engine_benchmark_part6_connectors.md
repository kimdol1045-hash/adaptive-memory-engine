# Adaptive Memory Engine Official Benchmark
# Part 6 — Connector Ingestion & Source Fidelity (Q151~Q165)

## Goal

Part 6 validates whether Slack/Jira/GitHub connector inputs become grounded memory.

검증 대상:

- Slack Export Connector
- Jira Issue/Comment Connector
- GitHub Issue/PR Connector
- Connector Decision Recall
- Connector Rationale Recall
- Source Citation Accuracy
- False Positive Resistance

---

# Category A — Connector Fact Recall (Q151~Q155)

## Q151
### Question
Slack architecture 채널에서 어떤 connector 결정이 있었지?

### Must Contain
- Slack Export Connector
- Hermes
- connector validation
- slack:architecture:1717890000.0001

---

## Q152
### Question
Jira AME-12 이슈는 무엇을 보존해야 한다고 했지?

### Must Contain
- Jira Issue/Comment Connector
- issue key
- comments
- jira:AME-12

---

## Q153
### Question
GitHub PR 42는 어떤 mapping을 추가했지?

### Must Contain
- GitHub Issue/PR Connector
- BronzeDocument
- PR comments
- github:pull_request:42

---

## Q154
### Question
connector source citation에서 중요한 것은?

### Must Contain
- Source Citation Accuracy
- Slack
- Jira
- GitHub

---

## Q155
### Question
Connector Contract는 왜 필요한가?

### Must Contain
- Connector Contract
- BronzeDocument
- OAuth
- transport

---

# Category B — Connector Decision & Rationale Recall (Q156~Q160)

## Q156
### Question
Slack Export를 OAuth보다 먼저 검증하는 이유는?

### Must Contain
- file based import
- connector quality
- OAuth risk
- rationale

---

## Q157
### Question
Jira connector 결정의 rationale은?

### Must Contain
- traceable issue context
- source citation accuracy
- Jira comments
- rationale

---

## Q158
### Question
GitHub connector 결정의 rationale은?

### Must Contain
- PR comments
- discussion
- source citations
- rationale

---

## Q159
### Question
Connector Benchmark에서 어떤 결정들이 추출되어야 하지?

### Must Contain
- Slack Export Connector
- Jira Issue/Comment Connector
- GitHub Issue/PR Connector
- Decision

---

## Q160
### Question
Connector 데이터에서 rationale memory가 만들어졌나?

### Must Contain
- rationale
- Slack Export Connector
- Jira Issue/Comment Connector
- GitHub Issue/PR Connector

---

# Category C — Source Fidelity (Q161~Q163)

## Q161
### Question
Slack 결정의 source는 어디인가?

### Must Contain
- slack
- architecture
- 1717890000.0001

---

## Q162
### Question
Jira 결정의 source는 어디인가?

### Must Contain
- jira
- AME-12

---

## Q163
### Question
GitHub 결정의 source는 어디인가?

### Must Contain
- github
- pull_request
- 42

---

# Category D — Connector Negative Recall (Q164~Q165)

## Q164
### Question
Connector benchmark에서 Pinecone을 사용하기로 했나?

### Must Contain
- Pinecone
- 존재하지

### Must Not Contain
- Pinecone을 사용한다

---

## Q165
### Question
Connector benchmark에서 OAuth가 이미 transport로 확정됐나?

### Must Contain
- OAuth
- risk
- transport
- 아직

### Must Not Contain
- OAuth transport 확정

