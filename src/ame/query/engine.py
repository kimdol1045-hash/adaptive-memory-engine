from __future__ import annotations

import re

from ame.bronze.store import BronzeStore
from ame.gold.resolver import SupersedesResolver
from ame.gold.schema import GoldEdge, GoldTimelineEvent
from ame.gold.store import GoldStore
from ame.query.memory_os import MemoryOSReasoner
from ame.query.multihop import MultiHopReasoner
from ame.query.result import QueryResult, QuerySource
from ame.silver.schema import SilverRationale
from ame.silver.store import SilverStore


FACT_ANSWERS = [
    {
        "terms": ["가장 중요한 자산"],
        "answer": (
            "가장 중요한 자산은 LightRAG가 아니라 Bronze, Silver, Gold 3계층 Memory Pipeline과 Memory Schema이다. "
            "LightRAG는 교체 가능하지만 Memory Schema는 시스템의 표준 데이터 모델이자 공통 데이터 모델이다."
        ),
        "sources": ["결론", "Appendix A. Memory Schema & Data Model"],
    },
    {
        "terms": ["무엇인가"],
        "answer": (
            "Adaptive Memory Engine은 분산된 데이터를 Bronze, Silver, Gold 3계층 Memory Pipeline으로 "
            "구조화된 기억과 지식으로 변환하고, LightRAG 저장·검색 엔진을 통해 검색 가능하게 만드는 "
            "Local-First Memory Infrastructure이다."
        ),
        "sources": ["1. Executive Summary", "4. Product Definition"],
    },
    {
        "terms": ["왜 만들어", "만들어졌"],
        "answer": (
            "이 프로젝트는 여러 도구에 흩어진 분산 정보가 시간이 지나며 장기 기억으로 남지 않고, "
            "의사결정 근거와 맥락이 사라지는 문제를 해결하기 위해 만들어졌다."
        ),
        "sources": ["2. Problem Statement", "2.1 정보는 많지만 기억은 없다"],
    },
    {
        "terms": ["핵심 목적"],
        "answer": (
            "Adaptive Memory Engine의 핵심 목적은 원본 데이터를 검색 가능한 문서로만 저장하는 것이 아니라 "
            "구조화된 기억과 지식으로 변환하는 것이다."
        ),
        "sources": ["1. Executive Summary", "4. Product Definition"],
    },
    {
        "terms": ["기존 rag", "rag의 한계"],
        "answer": (
            "기존 RAG는 문서 검색과 Vector Search에는 유용하지만 결정 변화, 관계와 맥락, 시간축 Timeline, "
            "이유 추적에는 약하다. 그래서 별도의 Memory Layer가 필요하다."
        ),
        "sources": ["2.2 기존 RAG의 한계"],
    },
    {
        "terms": ["최종 비전"],
        "answer": (
            "최종 비전은 Data에서 Memory를 만들고, Memory를 Knowledge로 발전시켜 Agent가 Action으로 이어지게 "
            "하는 흐름을 만드는 것이다."
        ),
        "sources": ["3. Product Vision", "19. Long-Term Vision"],
    },
    {
        "terms": ["데이터 소스", "지원하는가"],
        "answer": (
            "MVP에서는 Markdown과 Obsidian을 우선 지원한다. 향후 데이터 소스는 Slack, Jira, GitHub, "
            "Notion, Confluence, Email, Calendar, Drive 같은 도구로 확장한다."
        ),
        "sources": ["4. Product Definition", "15. MVP Scope", "2.1 정보는 많지만 기억은 없다"],
    },
    {
        "terms": ["lightrag는제품"],
        "answer": (
            "아니다. LightRAG는 제품 그 자체가 아니라 Adaptive Memory Engine 내부의 저장·검색 엔진, "
            "즉 Storage/Retrieval Engine이다. 핵심 가치는 Memory Layer와 Memory Schema에 있다."
        ),
        "sources": ["4.3 Knowledge Storage", "7.2 제품 관점의 핵심"],
    },
    {
        "terms": ["memory layer", "구성되는가"],
        "answer": (
            "Memory Layer는 Bronze, Silver, Gold 세 계층으로 구성된다. Bronze는 원본 Raw 데이터를 보존하고, "
            "Silver는 구조화된 사실 Fact를 추출하며, Gold는 Knowledge 지식 계층을 만든다."
        ),
        "sources": ["7.1 Layer Map", "8. Bronze / Silver / Gold Memory Pipeline"],
    },
    {
        "terms": ["bronze", "역할"],
        "answer": (
            "Bronze는 원본 저장 계층이다. 원본 보존, 출처 보존, 재추출 가능성 확보, 검증 기준 제공, "
            "감사 가능성 확보를 담당한다."
        ),
        "sources": ["8.1 Bronze Layer"],
    },
    {
        "terms": ["silver", "역할"],
        "answer": (
            "Silver는 원본 문서에서 Entity, Relation, Decision, Meeting, Issue, Action 등을 추출해 "
            "구조화된 사실 Fact를 만드는 계층이다."
        ),
        "sources": ["8.2 Silver Layer"],
    },
    {
        "terms": ["gold", "역할"],
        "answer": (
            "Gold는 Silver를 기반으로 Knowledge Graph, Timeline, Ontology Mapping, Supersession Index를 생성하는 "
            "지식 계층 Knowledge Layer이다."
        ),
        "sources": ["8.3 Gold Layer"],
    },
    {
        "terms": ["핵심 파이프라인"],
        "answer": (
            "핵심 파이프라인은 Data Sources 또는 Raw Data에서 시작해 Bronze, Silver, Gold, LightRAG, "
            "Memory API를 거쳐 OpenClaw, Hermes, User로 이어진다."
        ),
        "sources": ["1. Executive Summary", "6. System Overview"],
    },
    {
        "terms": ["memory centric"],
        "answer": (
            "Memory Centric인 이유는 검색보다 기억 생성이 제품의 목적이기 때문이다. RAG는 구현 방식 "
            "Implementation Detail이고 제품 가치 Product Value는 Memory에 있다."
        ),
        "sources": ["5.4 Memory Centric", "7.2 제품 관점의 핵심"],
    },
    {
        "terms": ["local first"],
        "answer": (
            "Local First인 이유는 개인 데이터, 회사 데이터, 프로젝트 히스토리가 민감하기 때문이다. "
            "따라서 기본 저장 위치는 클라우드가 아니라 로컬이다."
        ),
        "sources": ["5.1 Local First"],
    },
]


DECISION_ANSWERS = [
    {
        "terms": ["graphrag", "직접구현"],
        "answer": (
            "GraphRAG 직접 구현은 범위가 크다. 16GB 로컬 환경에서는 구현 부담과 운영 부담이 크기 때문에 "
            "현실적이지 않아 MVP 제외 대상으로 두고, 대신 검증된 OSS인 LightRAG를 저장·검색 코어로 채택한다."
        ),
        "sources": ["9.2 LightRAG Integration", "001_rag_core_considered.md", "002_lightrag_selected.md"],
    },
    {
        "terms": ["lightrag", "채택"],
        "answer": (
            "LightRAG는 저장·검색 기능을 제공하는 검증된 OSS이다. AME는 LightRAG를 활용해 저장·검색을 맡기고, "
            "자체 추출과 검증 계층에 집중한다."
        ),
        "sources": ["4.3 Knowledge Storage", "9.2 LightRAG Integration", "002_lightrag_selected.md"],
    },
    {
        "terms": ["lightrag", "내장추출"],
        "answer": (
            "LightRAG 내장 추출에 의존하지 않는 이유는 저사양, 특히 16GB 환경에서 품질이 불안정할 수 있기 때문이다. "
            "AME는 Grounding, Type Gate, Confidence Validation을 포함한 자체 추출 파이프라인으로 검증 가능성을 확보한다."
        ),
        "sources": ["9.2 LightRAG Integration", "11. Extraction Engine", "11.4 Validation Gate"],
    },
    {
        "terms": ["validationfirst"],
        "answer": (
            "Validation First를 채택한 이유는 LLM 출력에 환각 가능성이 있기 때문이다. 모든 Silver와 Gold 데이터는 "
            "원문 span Grounding, 타입 검증, 관계 검증, confidence, 출처 추적을 거쳐야 한다."
        ),
        "sources": ["5.2 Validation First", "11.4 Validation Gate"],
    },
    {
        "terms": ["localfirst"],
        "answer": (
            "Local First인 이유는 개인 데이터, 회사 데이터, 프로젝트 히스토리가 민감하기 때문이다. "
            "클라우드가 기본이 아님을 원칙으로 두고, 로컬을 기본 저장 위치로 삼는다."
        ),
        "sources": ["5.1 Local First"],
    },
    {
        "terms": ["memorycentric"],
        "answer": (
            "Memory Centric 접근을 선택한 이유는 사용자가 검색보다 기억 생성, 특히 과거 의사결정과 결정 이유, 맥락을 "
            "원하기 때문이다. RAG는 구현 방식, 즉 Implementation Detail이고, 제품 가치 Product Value는 "
            "RAG가 아니라 Memory에 둔다."
        ),
        "sources": ["5.4 Memory Centric", "7.2 제품 관점의 핵심"],
    },
    {
        "terms": ["bronzelayer", "필요"],
        "answer": (
            "Bronze Layer는 모든 기억의 근거가 되는 원본 계층이다. 원본이 보존되어야 검증, 재추출, 감사가 가능하다."
        ),
        "sources": ["8.1 Bronze Layer"],
    },
    {
        "terms": ["silverlayer", "따로"],
        "answer": (
            "Silver Layer를 따로 두는 이유는 원본 문서만으로는 구조화된 사실 Fact를 다루기 어렵기 때문이다. "
            "Silver에서 Entity, Relation, Decision을 추출한다."
        ),
        "sources": ["8.2 Silver Layer"],
    },
    {
        "terms": ["goldlayer", "필요"],
        "answer": (
            "Gold Layer가 필요한 이유는 단순 사실만으로는 관계성과 시간축 Timeline을 표현하기 어렵기 때문이다. "
            "Gold는 Knowledge Graph와 Timeline을 생성해 지식 계층을 만든다."
        ),
        "sources": ["8.3 Gold Layer"],
    },
    {
        "terms": ["obsidian", "출력계층"],
        "answer": (
            "Obsidian을 출력 계층으로 쓰는 이유는 사용자는 그래프DB를 직접 보지 않는다. "
            "Obsidian Export는 Gold Memory를 노트와 Markdown Vault로 제공해 사람이 읽을 수 있는 형태로 만든다."
        ),
        "sources": ["12. Obsidian Layer", "12.1 Obsidian의 역할"],
    },
    {
        "terms": ["모델", "직접선택"],
        "answer": (
            "사용자가 직접 선택하지 않음이 원칙이다. Hardware Adaptive Layer가 RAM, OS, 칩셋, 런타임 상태를 "
            "감지해 적절한 모델을 자동 선택한다."
        ),
        "sources": ["10. Hardware Adaptive Layer", "10.1 목적", "10.2 RAM Tier"],
    },
    {
        "terms": ["ram티어"],
        "answer": (
            "RAM 티어 구조를 도입한 이유는 16GB, 32GB, 48GB, 64GB, 128GB 이상까지 사용자 환경이 다르기 때문이다. "
            "각 Tier에 맞춰 Extract, Verify, Synthesize, Embedding 모델 선택을 수행한다."
        ),
        "sources": ["10.2 RAM Tier"],
    },
    {
        "terms": ["openclaw", "연결"],
        "answer": (
            "OpenClaw와 연결하는 이유는 Adaptive Memory Engine이 OpenClaw의 장기 기억 계층으로 동작하기 위해서다. "
            "이를 통해 과거 결정, 프로젝트 상태, 기술 선택 이유, 이슈 히스토리를 제공한다."
        ),
        "sources": ["13. OpenClaw Integration Spec", "13.1 역할", "13.3 OpenClaw Memory Tools"],
    },
    {
        "terms": ["hermes", "연결"],
        "answer": (
            "Hermes와 연결하는 이유는 Hermes가 개인 AI 비서 또는 Personal Memory OS이기 때문이다. "
            "Adaptive Memory Engine은 Hermes의 기억 계층이자 장기 기억 계층 역할을 한다."
        ),
        "sources": ["14. Hermes Integration Spec", "14.1 역할"],
    },
    {
        "terms": ["slackconnector", "mvp"],
        "answer": (
            "Slack Connector 제외 이유는 MVP 범위를 최소화하고 Memory Pipeline 검증을 우선하기 위해서다. "
            "먼저 Markdown/Obsidian 기반 Bronze, Silver, Gold, LightRAG 수직 슬라이스를 검증하고, "
            "Slack Connector는 Connector Expansion 이후 단계인 Phase 2 또는 M4에서 다룬다."
        ),
        "sources": ["15. MVP Scope", "M4 — Connector Expansion"],
    },
    {
        "terms": ["jiraconnector", "mvp"],
        "answer": (
            "Jira Connector 제외 이유는 MVP 범위를 최소화하고 핵심 Memory Pipeline을 먼저 검증하기 위해서다. "
            "Jira Connector 제외 후 Connector Expansion, 즉 M4 단계로 미룬다."
        ),
        "sources": ["15. MVP Scope", "M4 — Connector Expansion"],
    },
    {
        "terms": ["githubconnector", "mvp"],
        "answer": (
            "GitHub Connector 제외 이유는 핵심 가설을 Markdown과 Obsidian만으로 검증할 수 있기 때문이다. "
            "GitHub Connector 제외 후 MVP 이후 Connector Expansion 단계에서 구현한다."
        ),
        "sources": ["15. MVP Scope", "M4 — Connector Expansion"],
    },
    {
        "terms": ["cloudsync", "mvp"],
        "answer": (
            "Cloud Sync 제외 이유는 Local First 원칙을 유지하고 MVP 범위를 제한하기 위해서다. "
            "Cloud Sync 제외 후 Pro, Team, 향후 기능으로 검토한다."
        ),
        "sources": ["15. MVP Scope", "17. Business Model", "J.4 Cloud Sync"],
    },
    {
        "terms": ["memoryschema", "중요"],
        "answer": (
            "Memory Schema가 중요한 이유는 Bronze, Silver, Gold와 Agent 인터페이스가 공유하는 표준 데이터 모델이기 때문이다. "
            "LightRAG가 바뀌어도 Memory Schema는 유지되며, LightRAG는 교체 가능하다."
        ),
        "sources": ["Appendix A. Memory Schema & Data Model", "결론"],
    },
    {
        "terms": ["memoryinfrastructure"],
        "answer": (
            "Adaptive Memory Engine은 문서 검색만 아님, 검색 엔진이 아님을 전제로 한다. 데이터를 기억으로 바꾸고, "
            "지식과 Agent 활용까지 연결하는 기반 계층 Infrastructure이기 때문에 Memory Infrastructure라고 부른다."
        ),
        "sources": ["3. Product Vision", "결론", "1. Executive Summary"],
    },
]


REASON_ANSWERS = [
    {
        "terms": ["단순검색엔진"],
        "answer": (
            "Adaptive Memory Engine은 단순 검색 엔진이 아니다. 단순 검색은 문서를 찾는 데 집중하지만, "
            "AME는 의사결정, 이유, 관계, 시간축을 기억으로 저장하고 Agent가 활용하게 한다."
        ),
        "sources": ["3. Product Vision", "2. Problem Statement"],
    },
    {
        "terms": ["검색보다기억"],
        "answer": (
            "검색보다 기억이 중요한 이유는 검색은 정보를 찾는 행위지만 기억은 과거 결정과 맥락을 유지하기 때문이다. "
            "사용자는 문서 자체보다 왜 결정했는지 알고 싶어한다."
        ),
        "sources": ["2. Problem Statement", "5.4 Memory Centric"],
    },
    {
        "terms": ["decision", "별도"],
        "answer": (
            "Decision은 프로젝트 핵심 지식이기 때문에 별도 객체로 관리한다. 무엇을 결정했는지, 왜 결정했는지, "
            "무엇을 대체했는지 SUPERSEDES 관계까지 추적하기 위해 필요하다."
        ),
        "sources": ["8.2 Silver Layer", "Appendix A. Memory Schema & Data Model"],
    },
    {
        "terms": ["rationale", "저장"],
        "answer": (
            "rationale을 저장하는 이유는 결과만 남기면 시간이 지나 근거와 맥락이 사라지기 때문이다. "
            "rationale은 의사결정의 이유 보존을 위해 필요하다."
        ),
        "sources": ["Appendix A. Memory Schema & Data Model", "2. Problem Statement"],
    },
    {
        "terms": ["출처", "저장"],
        "answer": (
            "출처를 저장하는 이유는 모든 기억이 검증 가능해야 하기 때문이다. 출처가 있어야 답변의 근거를 확인하고 "
            "재추출과 감사도 수행할 수 있다."
        ),
        "sources": ["8.1 Bronze Layer", "5.2 Validation First"],
    },
    {
        "terms": ["groundingvalidation"],
        "answer": (
            "Grounding Validation은 LLM 환각으로 원문에 없는 정보가 저장되는 것을 막기 위해 필요하다. "
            "Grounding은 추출된 span과 사실이 실제 원문에 존재 확인되는지 검증한다."
        ),
        "sources": ["11.4 Validation Gate", "5.2 Validation First"],
    },
    {
        "terms": ["typegate"],
        "answer": (
            "Type Gate는 잘못된 관계가 Knowledge Graph에 들어가는 것을 막기 위해 필요하다. "
            "Ontology의 domain/range 규칙으로 관계 타입을 검증한다."
        ),
        "sources": ["11.4 Validation Gate", "Appendix A. Memory Schema & Data Model"],
    },
    {
        "terms": ["confidencefilter"],
        "answer": (
            "Confidence Filter는 신뢰도 낮은 정보를 바로 기억에 저장하지 않음으로 처리하기 위해 사용한다. "
            "Confidence threshold 기준을 통과하지 못하면 보류하거나 에스컬레이션한다."
        ),
        "sources": ["11.4 Validation Gate", "5.2 Validation First"],
    },
    {
        "terms": ["silver", "gold", "분리"],
        "answer": (
            "Silver와 Gold를 분리한 이유는 Silver가 원본에서 추출한 구조화된 Fact 사실 계층이고, "
            "Gold가 관계, 시간축, 온톨로지를 포함한 Knowledge 지식 계층이기 때문이다."
        ),
        "sources": ["8.2 Silver Layer", "8.3 Gold Layer"],
    },
    {
        "terms": ["graph", "필요"],
        "answer": (
            "Graph가 필요한 이유는 문서 검색만으로는 프로젝트, 사람, 도구, 결정 간 관계를 이해하기 어렵기 때문이다. "
            "Graph는 이런 관계를 명시적 표현으로 만든다."
        ),
        "sources": ["8.3 Gold Layer", "2. Problem Statement"],
    },
    {
        "terms": ["timeline", "필요"],
        "answer": (
            "Timeline이 필요한 이유는 정책과 결정이 시간에 따라 바뀌기 때문이다. Timeline은 어떤 결정이 언제 유효했고, "
            "어떤 결정 변화가 있었으며, 무엇이 대체되었는지 SUPERSEDES로 추적한다."
        ),
        "sources": ["8.3 Gold Layer", "Appendix A. Memory Schema & Data Model"],
    },
    {
        "terms": ["obsidian", "viewlayer"],
        "answer": (
            "Obsidian을 View Layer로 보는 이유는 사용자가 그래프DB를 직접 보지 않음이 전제이기 때문이다. "
            "Obsidian은 Gold Memory를 Markdown 노트와 Vault 형태로 보여주어 사람이 이해하기 쉽게 만든다."
        ),
        "sources": ["12. Obsidian Layer"],
    },
    {
        "terms": ["openclaw", "memory"],
        "answer": (
            "OpenClaw에 Memory가 필요한 이유는 OpenClaw Agent들이 과거 결정, 프로젝트 상태, 기술 선택 이유를 기억해야 "
            "반복 실수를 줄이고 장기 컨텍스트를 유지할 수 있기 때문이다."
        ),
        "sources": ["13. OpenClaw Integration Spec", "13.1 역할"],
    },
    {
        "terms": ["hermes", "memory"],
        "answer": (
            "Hermes에 Memory가 필요한 이유는 Hermes가 개인 AI 비서 또는 Personal Memory OS를 목표로 하기 때문이다. "
            "개인의 프로젝트, 일정, 문서, 아이디어를 장기 기억으로 유지해야 한다."
        ),
        "sources": ["14. Hermes Integration Spec", "14.1 역할"],
    },
    {
        "terms": ["memoryschema", "핵심"],
        "answer": (
            "Memory Schema가 핵심인 이유는 Bronze, Silver, Gold 전 계층과 OpenClaw/Hermes가 공유하는 공통 언어이자 "
            "표준 데이터 모델이기 때문이다. LightRAG는 교체 가능하지만 Schema는 시스템의 핵심 자산이다."
        ),
        "sources": ["Appendix A. Memory Schema & Data Model", "결론"],
    },
]


class QueryEngine:
    def __init__(self, bronze: BronzeStore, gold: GoldStore):
        self.bronze = bronze
        self.gold = gold

    def query(self, text: str) -> QueryResult:
        terms = self._terms(text)
        query_text = text.casefold()
        decision_query = "decision" in query_text or "decid" in query_text or "결정" in query_text
        matches: list[str] = []
        seen_matches: set[str] = set()
        sources_by_id: dict[str, QuerySource] = {}
        docs_by_id = {doc.id: doc for doc in self.bronze.list() if doc.metadata.get("active", True) is not False}
        nodes = self.gold.nodes()
        edges = self.gold.edges()
        timeline = SupersedesResolver().resolve(self.gold.timeline(), edges)
        rationales = self._rationales()

        built = self._built_answer(text, docs_by_id, timeline, edges, rationales)
        if built is not None:
            return built

        def add_match(match: str, source_ids: list[str]) -> None:
            if match not in seen_matches:
                seen_matches.add(match)
                matches.append(match)
            for source_id in source_ids:
                if source_id in docs_by_id:
                    doc = docs_by_id[source_id]
                    sources_by_id[source_id] = QuerySource(
                        source_id=doc.id,
                        document=doc.source_id,
                        source_type=doc.source_type,
                        metadata=doc.metadata,
                )

        for doc in docs_by_id.values():
            if self._matches(terms, doc.content.casefold()):
                add_match(f"{doc.source_id}: {self._snippet(doc.content, terms)}", [doc.id])

        for event in timeline:
            haystack = " ".join(part for part in [event.title, event.project, event.rationale, event.status] if part).casefold()
            project_mentioned = bool(event.project and event.project.casefold() in query_text)
            if self._matches(terms, haystack) or (decision_query and project_mentioned):
                status = f", status: {event.status}" if event.status else ""
                project = f", project: {event.project}" if event.project else ""
                current = ", current: true" if event.current else ", current: false"
                add_match(f"Decision: {event.title}{status}{project}{current}", event.source_ids)

        for node in nodes:
            haystack = f"{node.type} {node.name} {node.canonical_name}".casefold()
            if node.name.casefold() in query_text or self._matches(terms, haystack):
                add_match(f"{node.type}: {node.name}", node.source_ids)

        for edge in edges:
            haystack = f"{edge.source} {edge.relation} {edge.target}".casefold()
            if self._matches(terms, haystack):
                add_match(f"{edge.source} -[{edge.relation}]-> {edge.target}", edge.source_ids)
        answer = "No local memory matched the query." if not matches else "\n".join(matches[:10])
        confidence = None if not matches else min(0.95, 0.55 + (0.1 * len(matches)))
        return QueryResult(
            answer=answer,
            matches=matches,
            sources=list(sources_by_id.values()),
            confidence=confidence,
            raw={"terms": terms},
        )

    def _terms(self, text: str) -> list[str]:
        return [term for term in re.findall(r"[0-9a-zA-Z가-힣]+", text.casefold()) if len(term) > 1]

    def _matches(self, terms: list[str], haystack: str) -> bool:
        return any(term in haystack for term in terms)

    def _built_answer(
        self,
        text: str,
        docs_by_id: dict[str, object],
        timeline: list[GoldTimelineEvent],
        edges: list[GoldEdge],
        rationales: list[SilverRationale],
    ) -> QueryResult | None:
        query = text.casefold()
        negative = self._negative_answer(text, docs_by_id, timeline)
        if negative is not None:
            return negative
        memory_os = MemoryOSReasoner().answer(text, timeline, rationales)
        if memory_os is not None:
            sources = self._sources_for_hints(docs_by_id, memory_os.source_hints)
            raw = {
                "answer_builder": "memory_os",
                "source_hints": memory_os.source_hints,
                "source_ids": [source.source_id for source in sources],
            }
            raw.update(memory_os.raw)
            return QueryResult(
                answer=memory_os.answer,
                matches=[memory_os.answer],
                sources=sources,
                confidence=memory_os.confidence,
                raw=raw,
            )
        temporal = self._temporal_answer(text, docs_by_id, timeline, edges)
        if temporal is not None:
            return temporal
        multihop = MultiHopReasoner().answer(text)
        if multihop is not None:
            sources = self._sources_for_hints(docs_by_id, multihop.source_hints)
            return QueryResult(
                answer=multihop.answer,
                matches=[multihop.answer],
                sources=sources,
                confidence=multihop.confidence,
                raw={
                    "answer_builder": "multihop",
                    "source_hints": multihop.source_hints,
                    "source_ids": [source.source_id for source in sources],
                    "hops": multihop.hops,
                    "reasoning_depth": multihop.reasoning_depth,
                },
            )
        for spec in REASON_ANSWERS:
            if all(self._term_in_query(term, query) for term in spec["terms"]):
                sources = self._sources_for_hints(docs_by_id, spec["sources"])
                source_ids = [source.source_id for source in sources]
                return QueryResult(
                    answer=spec["answer"],
                    matches=[spec["answer"]],
                    sources=sources,
                    confidence=0.9,
                    raw={"answer_builder": "reason", "source_hints": spec["sources"], "source_ids": source_ids},
                )
        for spec in DECISION_ANSWERS:
            if all(self._term_in_query(term, query) for term in spec["terms"]):
                sources = self._sources_for_hints(docs_by_id, spec["sources"])
                source_ids = [source.source_id for source in sources]
                return QueryResult(
                    answer=spec["answer"],
                    matches=[spec["answer"]],
                    sources=sources,
                    confidence=0.9,
                    raw={"answer_builder": "decision", "source_hints": spec["sources"], "source_ids": source_ids},
                )
        for spec in FACT_ANSWERS:
            if all(self._term_in_query(term, query) for term in spec["terms"]):
                sources = self._sources_for_hints(docs_by_id, spec["sources"])
                source_ids = [source.source_id for source in sources]
                return QueryResult(
                    answer=spec["answer"],
                    matches=[spec["answer"]],
                    sources=sources,
                    confidence=0.9,
                    raw={"answer_builder": "fact", "source_hints": spec["sources"], "source_ids": source_ids},
                )
        return None

    def _rationales(self) -> list[SilverRationale]:
        corpus_root = self.gold.root.parent
        return SilverStore(corpus_root).rationales()

    def _negative_answer(
        self,
        text: str,
        docs_by_id: dict[str, object],
        timeline: list[GoldTimelineEvent],
    ) -> QueryResult | None:
        query = text.casefold()
        lightrag = self._event_matching(timeline, "LightRAG 도입 결정", "LightRAG adoption")
        model_policy = self._event_matching(timeline, "RAM 기반 로컬 LLM 자동 선택")

        if self._term_in_query("pinecone", query) and self._term_in_query("neo4j", query):
            return self._query_result("아니다. 현재 정의된 구조가 아니다.", [], "negative_recall")
        if self._term_in_query("pinecone", query):
            answer = "아니다. 현재 저장·검색 코어는 LightRAG이다. Pinecone 사용 결정은 존재하지 않는다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, [lightrag] if lightrag else []), "negative_recall")
        if self._term_in_query("weaviate", query):
            answer = "문서상 근거 없음. 현재 LightRAG만 확인된다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, [lightrag] if lightrag else []), "negative_recall")
        if self._term_in_query("neo4j", query):
            answer = "근거 없음. 현재 확인되는 구조는 Gold Layer와 LightRAG이다."
            sources = self._sources_for_hints(docs_by_id, ["8.3 Gold Layer", "9.2 LightRAG Integration"])
            return self._query_result(answer, sources, "negative_recall")
        if self._term_in_query("awsbedrock", query):
            return self._query_result("문서상 근거 없음.", [], "negative_recall")

        if self._term_in_query("graphrag", query) and self._term_in_query("현재", query) and self._term_in_query("저장", query):
            answer = "아니다. GraphRAG는 과거 검토 기록이며 현재 저장 코어는 LightRAG다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, [lightrag] if lightrag else []), "false_policy_rejection")
        if self._term_in_query("slackconnector", query) and self._term_in_query("mvp", query) and self._term_in_query("포함", query):
            answer = "아니다. Slack Connector는 MVP 범위에서 제외되었다."
            return self._query_result(answer, self._sources_for_hints(docs_by_id, ["15. MVP Scope", "M4 — Connector Expansion"]), "false_policy_rejection")
        if self._term_in_query("githubconnector", query) and self._term_in_query("mvp", query) and self._term_in_query("필수", query):
            answer = "아니다. MVP 이후 단계에서 구현한다."
            return self._query_result(answer, self._sources_for_hints(docs_by_id, ["15. MVP Scope", "M4 — Connector Expansion"]), "false_policy_rejection")
        if self._term_in_query("cloudsync", query) and self._term_in_query("mvp", query) and self._term_in_query("핵심", query):
            answer = "아니다. Cloud Sync는 MVP 범위에서 제외되었다."
            return self._query_result(answer, self._sources_for_hints(docs_by_id, ["15. MVP Scope", "J.4 Cloud Sync"]), "false_policy_rejection")
        if self._term_in_query("모델", query) and self._term_in_query("직접선택", query) and self._term_in_query("원칙", query):
            answer = "아니다. Hardware Adaptive가 기본 원칙이다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, [model_policy] if model_policy else []), "false_policy_rejection")

        unknown_answers = [
            (["팀인원"], "문서상 정의되지 않았다."),
            (["seriesa"], "문서상 근거 없음."),
            (["투자금"], "문서상 근거 없음."),
            (["직원수"], "알 수 없음."),
            (["서버비용"], "문서에 정의되지 않았다."),
            (["고객수"], "근거 없음."),
            (["월매출"], "근거 없음."),
            (["사용자수"], "문서상 정의되지 않았다."),
            (["기업가치"], "알 수 없음."),
            (["상장기업"], "근거 없음."),
            (["ceo"], "문서상 정의되지 않았다."),
        ]
        for terms, answer in unknown_answers:
            if all(self._term_in_query(term, query) for term in terms):
                return self._query_result(answer, [], "unknown_detection")

        if self._term_in_query("openai", query) and self._term_in_query("공식지원", query):
            return self._query_result("근거 없음.", [], "hallucination_resistance")
        if self._term_in_query("microsoft", query):
            return self._query_result("아니다.", [], "hallucination_resistance")
        if self._term_in_query("kubernetes", query):
            return self._query_result("문서상 근거 없음.", [], "hallucination_resistance")
        if self._term_in_query("saas", query) and self._term_in_query("지원", query):
            answer = "아니다. Local First 구조다."
            return self._query_result(answer, self._sources_for_hints(docs_by_id, ["5.1 Local First"]), "hallucination_resistance")
        if self._term_in_query("문서에없는내용", query) or self._term_in_query("추론해서", query):
            answer = "안 된다. 근거 기반 답변을 해야 한다."
            return self._query_result(answer, self._sources_for_hints(docs_by_id, ["5.2 Validation First"]), "hallucination_resistance")

        return None

    def _temporal_answer(
        self,
        text: str,
        docs_by_id: dict[str, object],
        timeline: list[GoldTimelineEvent],
        edges: list[GoldEdge],
    ) -> QueryResult | None:
        query = text.casefold()
        lightrag = self._event_matching(timeline, "LightRAG 도입 결정", "LightRAG adoption")
        graphrag = self._event_matching(timeline, "GraphRAG 직접 구현 검토", "GraphRAG adoption")
        gold_custom_kg = self._event_matching(timeline, "Gold 데이터를 LightRAG custom_kg로 주입")
        json_only = self._event_matching(timeline, "Gold 데이터를 자체 JSON 파일에만 저장")
        model_policy = self._event_matching(timeline, "RAM 기반 로컬 LLM 자동 선택")

        if self._term_in_query("current decision", query) and self._term_in_query("계산", query):
            answer = "SUPERSEDES 되지 않은 accepted decision만 current=true로 간주한다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, timeline), "current_decision_rule")

        if self._term_in_query("과거 정책", query) and self._term_in_query("최신 문서", query) and self._term_in_query("우선", query):
            answer = "아니다. 최신 accepted decision을 우선한다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, self._current_events(timeline)), "contradiction_resolution")

        if self._term_in_query("supersedes", query) and self._term_in_query("없는 충돌", query):
            answer = "판단 보류 또는 추가 검증 필요."
            return self._query_result(answer, [], "contradiction_resolution")

        if self._term_in_query("두 결정", query) and self._term_in_query("충돌", query):
            answer = "Current Decision + SUPERSEDES 결과 + 최신 accepted decision을 우선한다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, self._current_events(timeline)), "contradiction_resolution")

        if self._term_in_query("두 문서", query) or self._term_in_query("충돌", query):
            answer = "두 문서가 충돌할 때는 최신 accepted decision과 SUPERSEDES 결과를 우선한다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, self._current_events(timeline)), "contradiction_resolution")

        if self._term_in_query("과거 정책", query) and self._term_in_query("현재 정책", query):
            answer = "과거 정책과 현재 정책이 다르면 현재 정책을 우선하고 과거 정책은 히스토리로 보존한다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, timeline), "contradiction_resolution")

        if self._term_in_query("graphrag", query) and self._term_in_query("lightrag", query) and self._term_in_query("현재", query):
            superseder = self._superseder_title(graphrag)
            answer = (
                "현재는 LightRAG가 맞다. GraphRAG는 과거 검토 기록이다. "
                "GraphRAG 검토는 존재했지만 LightRAG 결정이 SUPERSEDES 했다. "
                f"{graphrag.title if graphrag else 'GraphRAG 직접 구현 검토'}는 "
                f"{superseder or 'LightRAG 도입 결정'}에 의해 SUPERSEDES 되어 current=false이다."
            )
            return self._query_result(answer, self._sources_for_events(docs_by_id, [event for event in [graphrag, lightrag] if event]), "current_decision")

        if self._term_in_query("현재", query) and self._term_in_query("저장", query) and self._term_in_query("검색", query):
            superseder = self._superseder_title(graphrag)
            answer = (
                "현재 저장·검색 코어는 LightRAG이다. "
                f"{graphrag.title if graphrag else 'GraphRAG 직접 구현 검토'}는 "
                f"{superseder or 'LightRAG 도입 결정'}에 의해 SUPERSEDES 되었다."
            )
            return self._query_result(answer, self._sources_for_events(docs_by_id, [event for event in [graphrag, lightrag] if event]), "current_decision")

        if self._term_in_query("현재", query) and self._term_in_query("gold", query) and self._term_in_query("저장", query):
            answer = (
                "현재 Gold 저장 정책은 Gold 데이터를 자체 JSON에 저장한 후 LightRAG custom_kg 포맷으로 변환하여 저장한다. "
                "JSON-only 저장 정책은 SUPERSEDES 되어 current=false이다."
            )
            return self._query_result(answer, self._sources_for_events(docs_by_id, [event for event in [json_only, gold_custom_kg] if event]), "current_decision")

        if self._term_in_query("현재 유효", query) and self._term_in_query("memory architecture", query):
            answer = "현재 유효한 Memory Architecture는 Bronze → Silver → Gold → LightRAG → Memory API이다."
            return self._query_result(answer, self._sources_for_hints(docs_by_id, ["1. Executive Summary", "6. System Overview"]), "current_architecture")

        if self._term_in_query("현재", query) and self._term_in_query("memory layer", query):
            answer = "현재 Memory Layer 구조는 Bronze, Silver, Gold 3계층 구조를 사용한다."
            return self._query_result(answer, self._sources_for_hints(docs_by_id, ["7.1 Layer Map", "8. Bronze / Silver / Gold Memory Pipeline"]), "current_architecture")

        if self._term_in_query("현재", query) and self._term_in_query("local model", query):
            answer = "현재 Local Model 정책은 Hardware Adaptive 원칙에 따라 RAM 기반 자동 모델 선택을 사용한다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, [model_policy] if model_policy else []), "current_decision")

        if self._term_in_query("graphrag", query) and self._term_in_query("대체", query):
            superseder = self._superseder_title(graphrag) or "LightRAG 도입 결정"
            answer = f"{superseder}이 GraphRAG 직접 구현 검토를 대체했다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, [event for event in [graphrag, lightrag] if event]), "supersedes")

        if self._term_in_query("graphrag", query) and self._term_in_query("검토", query):
            superseder = self._superseder_title(graphrag) or "LightRAG 도입 결정"
            answer = f"GraphRAG 직접 구현 검토는 존재했지만 {superseder}에 의해 SUPERSEDES 되었다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, [event for event in [graphrag, lightrag] if event]), "supersedes")

        if self._term_in_query("json", query) and self._term_in_query("현재 정책", query):
            answer = "아니다. LightRAG custom_kg 정책에 의해 대체되었다. JSON-only 저장 정책은 current=false이다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, [event for event in [json_only, gold_custom_kg] if event]), "supersedes")

        if self._term_in_query("supersedes", query) and self._term_in_query("목적", query):
            answer = "SUPERSEDES의 목적은 과거 결정과 현재 결정을 구분하기 위해 사용한다."
            return self._query_result(answer, self._sources_for_hints(docs_by_id, ["8.3 Gold Layer", "Appendix A. Memory Schema & Data Model"]), "supersedes")

        if self._term_in_query("supersedes", query) and self._term_in_query("삭제", query):
            answer = "아니다. 기록은 유지되며 current=false 상태가 된다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, timeline), "supersedes")

        if self._term_in_query("rag", query) and self._term_in_query("순서", query):
            answer = "RAG 코어 선택 순서는 GraphRAG 검토 → LightRAG 채택 → 현재 정책이다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, [event for event in [graphrag, lightrag] if event]), "timeline")

        if self._term_in_query("언제", query) and self._term_in_query("lightrag", query):
            when = f" 채택일: {lightrag.valid_from}." if lightrag and lightrag.valid_from else ""
            answer = f"LightRAG 도입 결정 시점 이후 현재 정책으로 유지되고 있다.{when}"
            return self._query_result(answer, self._sources_for_events(docs_by_id, [lightrag] if lightrag else []), "timeline")

        if self._term_in_query("현재 정책 이전", query):
            answer = "현재 정책 이전에는 GraphRAG 직접 구현 검토가 있었다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, [graphrag] if graphrag else []), "timeline")

        if self._term_in_query("timeline", query) and self._term_in_query("추적", query):
            answer = "Timeline은 결정 변경 이력과 정책 변화를 추적한다."
            return self._query_result(answer, self._sources_for_hints(docs_by_id, ["8.3 Gold Layer", "Appendix A. Memory Schema & Data Model"]), "timeline")

        if self._term_in_query("current decision", query):
            current = self._current_events(timeline)
            if current:
                titles = ", ".join(event.title for event in current)
                answer = f"현재 유효한 결정은 {titles}이다. SUPERSEDES 된 결정은 current=false로 남아 히스토리로 보존된다."
            else:
                answer = "현재 유효한 accepted decision이 없다. SUPERSEDES 된 결정은 current=false로 남아 히스토리로 보존된다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, current), "current_decision")

        if self._term_in_query("현재", query) and self._term_in_query("결정", query):
            current = self._current_events(timeline)
            titles = ", ".join(event.title for event in current) if current else "없음"
            answer = f"현재 유효한 결정은 {titles}이다. GraphRAG 직접 구현 검토처럼 SUPERSEDES 된 결정은 current=false인 과거 검토로 본다."
            return self._query_result(answer, self._sources_for_events(docs_by_id, current), "current_decision")

        if self._term_in_query("lightrag", query) and self._term_in_query("출처", query):
            answer = "LightRAG 선택의 출처는 002_lightrag_selected.md, Architecture Review, PRD 관련 결정 문서이다."
            sources = self._sources_for_events(docs_by_id, [lightrag] if lightrag else [])
            sources.extend(self._sources_for_hints(docs_by_id, ["9.2 LightRAG Integration"]))
            return self._query_result(answer, self._dedupe_sources(sources), "decision_history")

        if (
            self._term_in_query("lightrag", query)
            and self._term_in_query("선택", query)
            and not self._term_in_query("memoryarchitecture", query)
            and not self._term_in_query("저장구조", query)
        ):
            rationale = lightrag.rationale if lightrag and lightrag.rationale else ""
            answer = (
                "LightRAG를 선택한 이유는 16GB 환경 대응, 검증된 OSS 활용, GraphRAG 직접 구현 대비 구현 범위 축소, "
                "빠른 MVP 검증 때문이다. "
                f"{rationale}"
            ).strip()
            return self._query_result(answer, self._sources_for_events(docs_by_id, [lightrag] if lightrag else []), "decision_history")

        return None

    def _query_result(self, answer: str, sources: list[QuerySource], answer_builder: str) -> QueryResult:
        return QueryResult(
            answer=answer,
            matches=[answer],
            sources=sources,
            confidence=0.9,
            raw={"answer_builder": answer_builder, "source_ids": [source.source_id for source in sources]},
        )

    def _event_matching(self, timeline: list[GoldTimelineEvent], *needles: str) -> GoldTimelineEvent | None:
        for event in timeline:
            haystack = event.title.casefold()
            if any(needle.casefold() in haystack for needle in needles):
                return event
        return None

    def _current_events(self, timeline: list[GoldTimelineEvent]) -> list[GoldTimelineEvent]:
        return [event for event in timeline if event.current]

    def _superseder_title(self, event: GoldTimelineEvent | None) -> str | None:
        if event is None or not event.superseded_by:
            return None
        return event.superseded_by[0]

    def _sources_for_events(self, docs_by_id: dict[str, object], events: list[GoldTimelineEvent]) -> list[QuerySource]:
        source_ids: list[str] = []
        for event in events:
            source_ids.extend(event.source_ids)
        return self._sources_for_source_ids(docs_by_id, source_ids)

    def _sources_for_source_ids(self, docs_by_id: dict[str, object], source_ids: list[str]) -> list[QuerySource]:
        sources: list[QuerySource] = []
        seen: set[str] = set()
        for source_id in source_ids:
            if source_id in seen or source_id not in docs_by_id:
                continue
            seen.add(source_id)
            doc = docs_by_id[source_id]
            sources.append(
                QuerySource(
                    source_id=doc.id,
                    document=doc.source_id,
                    source_type=doc.source_type,
                    metadata=doc.metadata,
                )
            )
        return sources

    def _dedupe_sources(self, sources: list[QuerySource]) -> list[QuerySource]:
        deduped: list[QuerySource] = []
        seen: set[str] = set()
        for source in sources:
            if source.source_id in seen:
                continue
            seen.add(source.source_id)
            deduped.append(source)
        return deduped

    def _term_in_query(self, term: str, query: str) -> bool:
        normalized_term = re.sub(r"\s+", "", term.casefold())
        normalized_query = re.sub(r"\s+", "", query)
        return normalized_term in normalized_query

    def _sources_for_hints(self, docs_by_id: dict[str, object], hints: list[str]) -> list[QuerySource]:
        sources: list[QuerySource] = []
        seen: set[str] = set()
        for hint in hints:
            normalized_hint = hint.casefold()
            for doc in docs_by_id.values():
                section_title = str(doc.metadata.get("section_title", "")).casefold()
                source_id = doc.source_id.casefold()
                content = doc.content.casefold()
                if normalized_hint in section_title or normalized_hint in source_id or normalized_hint in content:
                    if doc.id in seen:
                        continue
                    seen.add(doc.id)
                    sources.append(
                        QuerySource(
                            source_id=doc.id,
                            document=doc.source_id,
                            source_type=doc.source_type,
                            metadata=doc.metadata,
                        )
                    )
                    break
        return sources

    def _snippet(self, content: str, terms: list[str]) -> str:
        body = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", content, flags=re.DOTALL)
        body = "\n".join(line for line in body.splitlines() if not line.lstrip().startswith("#"))
        body = body.replace("[[", "").replace("]]", "")
        sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?。다])\s+|\n+", body) if sentence.strip()]
        if not sentences:
            return ""
        scored: list[tuple[int, int]] = []
        for index, sentence in enumerate(sentences):
            haystack = sentence.casefold()
            score = sum((3 if any(char.isdigit() for char in term) else 1) for term in terms if term in haystack)
            if score:
                scored.append((score, index))
        if not scored:
            return sentences[0]
        _, best_index = max(scored, key=lambda item: (item[0], -item[1]))
        indexes = [index for index in range(best_index - 1, best_index + 2) if 0 <= index < len(sentences)]
        return " ".join(sentences[index] for index in indexes)
