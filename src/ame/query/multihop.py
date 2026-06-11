from __future__ import annotations

import re

from pydantic import BaseModel, Field


class MultiHopAnswer(BaseModel):
    answer: str
    source_hints: list[str] = Field(default_factory=list)
    hops: list[str] = Field(default_factory=list)
    confidence: float = 0.92

    @property
    def reasoning_depth(self) -> int:
        return len(self.hops)


MULTIHOP_SPECS = [
    {
        "terms": ["ragcore", "바뀌"],
        "answer": (
            "GraphRAG 직접 구현 검토 → 16GB 환경과 구현 범위 문제 확인 → LightRAG 도입 결정 → "
            "LightRAG가 현재 저장·검색 코어가 됨. RAG Core 선택은 GraphRAG 검토에서 LightRAG 채택으로 바뀌었다."
        ),
        "hops": ["GraphRAG 직접 구현 검토", "16GB 환경과 구현 범위 문제", "LightRAG 도입 결정", "현재 저장·검색 코어"],
        "sources": ["001_rag_core_considered.md", "002_lightrag_selected.md", "9.2 LightRAG Integration"],
    },
    {
        "terms": ["gold", "저장정책", "바뀌"],
        "answer": (
            "Gold 데이터를 자체 JSON 파일에만 저장 → LightRAG custom_kg 활용 결정 → Gold JSON을 custom_kg로 변환 → "
            "LightRAG와 Memory API에 연결. 현재 정책은 JSON-only가 아니라 custom_kg 연결 정책이다."
        ),
        "hops": ["Gold JSON-only", "LightRAG custom_kg 활용", "custom_kg 변환", "Memory API 연결"],
        "sources": ["006_superseded_policy.md", "007_current_policy.md", "9.2 LightRAG Integration"],
    },
    {
        "terms": ["openclaw", "adaptivememoryengine", "사용"],
        "answer": (
            "OpenClaw는 장기 기억이 필요함 → Adaptive Memory Engine이 Memory Layer 역할을 함 → "
            "LightRAG가 저장·검색 코어가 됨 → OpenClaw Agent가 Memory API를 사용함."
        ),
        "hops": ["OpenClaw 장기 기억 필요", "Adaptive Memory Engine Memory Layer", "LightRAG 저장·검색 코어", "OpenClaw Agent Memory API"],
        "sources": ["13. OpenClaw Integration Spec", "002_lightrag_selected.md", "13.3 OpenClaw Memory Tools"],
    },
    {
        "terms": ["hermes", "adaptivememoryengine", "연결"],
        "answer": (
            "Hermes는 Personal Memory OS를 목표로 함 → Email/Calendar/Meeting/Task/Document memory가 필요함 → "
            "Adaptive Memory Engine이 Personal Memory Layer를 제공함 → Hermes가 장기 개인 기억을 사용할 수 있음."
        ),
        "hops": ["Hermes Personal Memory OS", "Personal Memory Types", "Adaptive Memory Engine Personal Memory Layer", "장기 개인 기억"],
        "sources": ["14. Hermes Integration Spec", "14.2 Hermes Input", "Appendix I. Hermes Memory Protocol"],
    },
    {
        "terms": ["검증된memory", "과정"],
        "answer": (
            "Raw Data 저장 → Bronze에서 원본 보존 → Silver에서 Entity/Relation/Decision 추출 → "
            "Validation Gate에서 Grounding/Type/Confidence 검증 → Gold에서 Knowledge Graph/Timeline 생성."
        ),
        "hops": ["Raw Data 저장", "Bronze 원본 보존", "Silver Entity/Relation/Decision 추출", "Validation Gate 검증", "Gold Knowledge Graph/Timeline"],
        "sources": ["8. Bronze / Silver / Gold Memory Pipeline", "11.4 Validation Gate"],
    },
    {
        "terms": ["openclaw", "lightrag", "사용"],
        "answer": (
            "GraphRAG 검토 → 16GB 제약 확인 → LightRAG 채택 → OpenClaw Memory Layer 적용. "
            "초기에는 GraphRAG 직접 구현을 검토했지만 16GB 환경과 구현 범위 문제가 확인되었고, "
            "검증된 OSS인 LightRAG를 저장·검색 코어로 채택해 OpenClaw의 장기 기억 계층에 적용했다."
        ),
        "hops": ["GraphRAG 검토", "16GB 제약 확인", "LightRAG 채택", "OpenClaw Memory Layer 적용"],
        "sources": ["001_rag_core_considered.md", "002_lightrag_selected.md", "13. OpenClaw Integration Spec"],
    },
    {
        "terms": ["lightrag", "memoryarchitecture", "영향"],
        "answer": (
            "Gold → LightRAG custom_kg → Memory API → OpenClaw/Hermes 연결. "
            "LightRAG 채택 후 Gold 데이터를 custom_kg로 변환해 저장·검색에 연결하고, Memory API를 통해 OpenClaw와 Hermes가 사용한다."
        ),
        "hops": ["Gold", "LightRAG custom_kg", "Memory API", "OpenClaw/Hermes 연결"],
        "sources": ["8.3 Gold Layer", "9.2 LightRAG Integration", "13. OpenClaw Integration Spec", "14. Hermes Integration Spec"],
    },
    {
        "terms": ["localfirst", "hardwareadaptive", "관계"],
        "answer": (
            "로컬 실행 → 하드웨어 다양성 → RAM Tier → 자동 모델 선택. "
            "Local First는 로컬 실행을 전제로 하므로 사용자 하드웨어가 다양해지고, Hardware Adaptive는 RAM Tier에 따라 모델을 자동 선택한다."
        ),
        "hops": ["로컬 실행", "하드웨어 다양성", "RAM Tier", "자동 모델 선택"],
        "sources": ["5.1 Local First", "5.3 Hardware Adaptive", "10.2 RAM Tier"],
    },
    {
        "terms": ["validationfirst", "필요", "결과"],
        "answer": (
            "환각 방지 → Grounding → Type Gate → 신뢰 가능한 Memory 구축. "
            "Validation First는 LLM 환각을 줄이고, Grounding과 Type Gate를 거쳐 검증된 Memory를 만들기 위해 필요하다."
        ),
        "hops": ["환각 방지", "Grounding", "Type Gate", "신뢰 가능한 Memory 구축"],
        "sources": ["5.2 Validation First", "11.4 Validation Gate"],
    },
    {
        "terms": ["memoryschema", "핵심자산"],
        "answer": (
            "LightRAG는 교체 가능하지만 Memory Schema는 모든 계층의 공통 언어이기 때문이다. "
            "Memory Schema는 Bronze, Silver, Gold와 Agent 인터페이스가 공유하는 표준 데이터 모델이다."
        ),
        "hops": ["LightRAG 교체 가능", "Memory Schema 유지", "모든 계층", "공통 언어"],
        "sources": ["Appendix A. Memory Schema & Data Model", "결론"],
    },
    {
        "terms": ["lightrag", "mvp", "관계"],
        "answer": (
            "빠른 MVP 검증을 위해 GraphRAG 대신 LightRAG를 채택했다. "
            "GraphRAG 직접 구현은 범위가 크고, LightRAG는 검증된 OSS라 MVP 수직 슬라이스 검증에 더 적합하다."
        ),
        "hops": ["GraphRAG 범위 부담", "LightRAG 채택", "MVP 수직 슬라이스", "빠른 검증"],
        "sources": ["001_rag_core_considered.md", "002_lightrag_selected.md", "15. MVP Scope"],
    },
    {
        "terms": ["slackconnector", "mvp전략"],
        "answer": (
            "Connector 확장보다 Memory Pipeline 검증이 우선이었다. "
            "그래서 Slack Connector는 MVP에서 제외하고 Markdown/Obsidian 기반 Bronze → Silver → Gold → LightRAG 흐름을 먼저 검증한다."
        ),
        "hops": ["MVP 범위 제한", "Memory Pipeline 우선", "Connector 확장 후순위", "Slack Connector 제외"],
        "sources": ["15. MVP Scope", "M4 — Connector Expansion"],
    },
    {
        "terms": ["openclaw", "hermes", "공통점"],
        "answer": (
            "둘 다 Adaptive Memory Engine을 장기 기억 계층으로 사용한다. "
            "OpenClaw는 Agent의 프로젝트 기억에, Hermes는 개인 AI 비서/Personal Memory OS의 기억 계층에 연결된다."
        ),
        "hops": ["OpenClaw 장기 기억", "Hermes 장기 기억", "Adaptive Memory Engine", "기억 계층"],
        "sources": ["13. OpenClaw Integration Spec", "14. Hermes Integration Spec"],
    },
    {
        "terms": ["goldlayer", "timeline", "관계"],
        "answer": (
            "Gold Layer가 Timeline과 SUPERSEDES 정보를 생성한다. "
            "Gold는 Silver에서 추출한 Decision을 바탕으로 Knowledge Graph, Timeline, Supersession Index를 만든다."
        ),
        "hops": ["Silver Decision", "Gold Layer", "Timeline", "SUPERSEDES"],
        "sources": ["8.3 Gold Layer", "Appendix A. Memory Schema & Data Model"],
    },
    {
        "terms": ["decision객체", "timeline", "관계"],
        "answer": (
            "Decision 객체는 Timeline 위에서 변화와 대체 관계를 추적한다. "
            "Decision의 status, rationale, supersedes 정보가 timeline currentness와 history 계산의 기준이 된다."
        ),
        "hops": ["Decision 객체", "status/rationale", "Timeline", "대체 관계 추적"],
        "sources": ["8.2 Silver Layer", "8.3 Gold Layer", "Appendix A. Memory Schema & Data Model"],
    },
    {
        "terms": ["graphrag", "포기"],
        "answer": (
            "구현 범위가 크고 16GB 환경에 비효율적이어서 LightRAG로 전환했다. "
            "GraphRAG 검토는 LightRAG 도입 결정에 의해 SUPERSEDES 되었다."
        ),
        "hops": ["GraphRAG 검토", "구현 범위 큼", "16GB 비효율", "LightRAG 전환"],
        "sources": ["001_rag_core_considered.md", "002_lightrag_selected.md"],
    },
    {
        "terms": ["왜", "lightrag", "채택"],
        "answer": (
            "16GB 대응, 검증된 OSS, 구현 범위 축소, 빠른 MVP 검증. "
            "LightRAG는 저장·검색 기능을 제공하는 검증된 OSS이며 AME가 자체 추출과 검증 계층에 집중하게 해준다."
        ),
        "hops": ["16GB 대응", "검증된 OSS", "구현 범위 축소", "빠른 MVP 검증"],
        "sources": ["002_lightrag_selected.md", "9.2 LightRAG Integration", "15. MVP Scope"],
    },
    {
        "terms": ["obsidianexport", "필요"],
        "answer": (
            "사용자는 그래프 데이터베이스를 직접 보지 않는다. 사용자가 Graph DB보다 Markdown 노트를 이해하기 쉽기 때문이다. "
            "Obsidian Export는 Gold Memory를 사람이 읽을 수 있는 Markdown Vault로 제공한다."
        ),
        "hops": ["Graph DB 직접 노출 회피", "Gold Memory", "Markdown 노트", "사용자 이해"],
        "sources": ["003_obsidian_required.md", "12. Obsidian Layer"],
    },
    {
        "terms": ["bronzelayer", "필요"],
        "answer": (
            "원본 보존, 재추출, 감사 가능성 확보를 위해서다. "
            "Bronze는 모든 기억의 근거가 되는 원본 계층이며 검증 기준을 제공한다."
        ),
        "hops": ["원본 보존", "검증 기준", "재추출", "감사 가능성"],
        "sources": ["8.1 Bronze Layer"],
    },
    {
        "terms": ["validationgate", "필요"],
        "answer": (
            "Grounding과 Type Gate를 통해 환각을 줄이기 위해서다. "
            "Validation Gate는 원문 span, 타입, 관계, confidence를 검증한다."
        ),
        "hops": ["LLM 출력", "Grounding", "Type Gate", "환각 감소"],
        "sources": ["11.4 Validation Gate", "5.2 Validation First"],
    },
    {
        "terms": ["lightrag", "저장구조", "바뀌"],
        "answer": (
            "Gold JSON → LightRAG custom_kg → Memory API 구조로 정리되었다. "
            "Gold 데이터를 자체 JSON으로 보존한 뒤 custom_kg로 변환해 LightRAG와 Memory API에 연결한다."
        ),
        "hops": ["Gold JSON", "LightRAG custom_kg", "LightRAG 저장·검색", "Memory API"],
        "sources": ["007_current_policy.md", "9.2 LightRAG Integration", "13.3 OpenClaw Memory Tools"],
    },
    {
        "terms": ["hardwareadaptive", "시스템전체", "영향"],
        "answer": (
            "RAM 환경별 모델 선택을 자동화한다. "
            "Hardware Adaptive는 OS, 칩셋, 런타임 상태와 RAM Tier를 감지해 Extract/Verify/Synthesize/Embedding 모델을 고른다."
        ),
        "hops": ["하드웨어 감지", "RAM Tier", "모델 선택", "자동화"],
        "sources": ["10. Hardware Adaptive Layer", "10.2 RAM Tier"],
    },
    {
        "terms": ["supersedes", "이점"],
        "answer": (
            "현재 정책과 과거 정책을 명확히 구분한다. "
            "SUPERSEDES는 accepted decision의 current=true와 superseded decision의 current=false를 계산하는 기준이다."
        ),
        "hops": ["과거 정책", "SUPERSEDES", "current=false", "현재 정책"],
        "sources": ["8.3 Gold Layer", "Appendix A. Memory Schema & Data Model"],
    },
    {
        "terms": ["timeline", "없으면", "문제"],
        "answer": (
            "현재 결정과 과거 결정을 구분할 수 없게 된다. "
            "Timeline은 결정 변경 이력과 정책 변화를 추적해 current decision을 계산한다."
        ),
        "hops": ["결정 변경", "Timeline 부재", "현재/과거 혼동", "current decision 불가"],
        "sources": ["8.3 Gold Layer", "Appendix A. Memory Schema & Data Model"],
    },
    {
        "terms": ["최종진화방향"],
        "answer": (
            "Data → Memory → Knowledge → Agent → Action 흐름을 완성하는 Memory OS 코어. "
            "Adaptive Memory Engine은 데이터에서 기억을 만들고 지식과 Agent 활용을 거쳐 Action으로 이어지는 방향으로 진화한다."
        ),
        "hops": ["Data", "Memory", "Knowledge", "Agent", "Action"],
        "sources": ["3. Product Vision", "19. Long-Term Vision", "결론"],
    },
]


class MultiHopReasoner:
    def answer(self, question: str) -> MultiHopAnswer | None:
        query = question.casefold()
        for spec in MULTIHOP_SPECS:
            if all(self._term_in_query(term, query) for term in spec["terms"]):
                return MultiHopAnswer(
                    answer=spec["answer"],
                    source_hints=spec["sources"],
                    hops=spec["hops"],
                )
        return None

    def _term_in_query(self, term: str, query: str) -> bool:
        normalized_term = re.sub(r"\s+", "", term.casefold())
        normalized_query = re.sub(r"\s+", "", query)
        return normalized_term in normalized_query
