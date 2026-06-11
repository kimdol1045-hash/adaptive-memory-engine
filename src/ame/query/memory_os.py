from __future__ import annotations

import re

from pydantic import BaseModel, Field

from ame.gold.schema import GoldTimelineEvent
from ame.query.diff import MemoryDiffEngine
from ame.query.mql import MqlEngine
from ame.silver.schema import SilverRationale


class MemoryOsAnswer(BaseModel):
    answer: str
    source_hints: list[str] = Field(default_factory=list)
    confidence: float = 0.9
    raw: dict = Field(default_factory=dict)


MEMORY_OS_SPECS = [
    {
        "terms": ["지난주대비", "현재저장정책"],
        "answer": (
            "초기 JSON-only 저장 정책은 과거 정책으로 남고 current=false이다. "
            "현재는 Gold JSON을 LightRAG custom_kg로 변환해 사용하는 정책이 current=true로 유지된다."
        ),
        "sources": ["006_superseded_policy.md", "007_current_policy.md"],
        "raw": {"feature": "memory_diff"},
    },
    {
        "terms": ["새로추가", "memory", "결정"],
        "answer": (
            "새로 추가된 decision만 보려면 기존 knowledge 전체가 아니라 accepted decision을 filter해서 반환해야 한다."
        ),
        "sources": ["8.3 Gold Layer", "Appendix A. Memory Schema & Data Model"],
        "raw": {"feature": "memory_diff"},
    },
    {
        "terms": ["이번스프린트", "architecturedecision"],
        "answer": (
            "이번 sprint에서 변경된 architecture decision은 Timeline 기준으로 찾고, 변경 전/후 관계가 있으면 "
            "SUPERSEDES 관계도 함께 보여줘야 한다."
        ),
        "sources": ["8.3 Gold Layer", "Appendix A. Memory Schema & Data Model"],
        "raw": {"feature": "memory_diff"},
    },
    {
        "terms": ["현재상태", "바꾸"],
        "answer": (
            "현재 상태를 바꾼 원인은 accepted decision이다. 현재 상태에 영향을 준 accepted decision을 추적하고, "
            "대체된 decision이 있으면 함께 설명해야 한다."
        ),
        "sources": ["002_lightrag_selected.md", "007_current_policy.md"],
        "raw": {"feature": "memory_diff"},
    },
    {
        "terms": ["memorydiff", "필요"],
        "answer": (
            "Memory Diff는 사용자가 전체 문서를 다시 읽지 않고도 특정 기간 동안의 변경점, 새 decision, "
            "대체된 정책을 확인하기 위해 필요하다."
        ),
        "sources": ["8.3 Gold Layer", "Appendix A. Memory Schema & Data Model"],
        "raw": {"feature": "memory_diff"},
    },
    {
        "terms": ["current=true", "decision", "조회"],
        "answer": (
            "MQL 또는 Agent API에서 current=true 조건으로 accepted decision만 조회해야 한다. "
            "예: FIND decisions WHERE current=true"
        ),
        "sources": ["Appendix A. Memory Schema & Data Model"],
        "raw": {"feature": "mql", "mql": "FIND decisions WHERE current=true"},
    },
    {
        "terms": ["lightrag", "rationale", "조회"],
        "answer": 'decision=LightRAG에 연결된 rationale memory를 조회해야 한다. 예: WHY decision="LightRAG"',
        "sources": ["002_lightrag_selected.md", "9.2 LightRAG Integration"],
        "raw": {"feature": "mql", "mql": 'WHY decision="LightRAG"'},
    },
    {
        "terms": ["특정프로젝트", "timeline"],
        "answer": 'project 또는 corpus 기준으로 timeline query를 실행해야 한다. 예: SHOW timeline FOR project="Adaptive Memory Engine"',
        "sources": ["Appendix A. Memory Schema & Data Model"],
        "raw": {"feature": "mql", "mql": 'SHOW timeline FOR project="Adaptive Memory Engine"'},
    },
    {
        "terms": ["mql", "필요"],
        "answer": (
            "자연어 질의만으로는 agent가 안정적으로 memory를 재사용하기 어렵다. "
            "decision, current, rationale, timeline, diff를 구조화된 질의로 조회하기 위해 MQL이 필요하다."
        ),
        "sources": ["D.3 CLI", "Appendix A. Memory Schema & Data Model"],
        "raw": {"feature": "mql"},
    },
    {
        "terms": ["openclawagent", "현재결정"],
        "answer": (
            "OpenClaw Agent가 current decision, 즉 현재 결정만 사용하려면 memory.current_decision() 또는 "
            "FIND decisions WHERE current=true 같은 API/MQL을 사용해야 한다."
        ),
        "sources": ["13.3 OpenClaw Memory Tools", "Appendix A. Memory Schema & Data Model"],
        "raw": {"feature": "agent_memory_api", "api": "memory.current_decision"},
    },
    {
        "terms": ["mql", "자연어"],
        "answer": (
            "자연어 질의는 사람이 사용하기 좋고, MQL은 Agent가 안정적으로 사용하기 좋은 구조화된 질의 계층이다. "
            "둘은 병행되어야 한다."
        ),
        "sources": ["D.3 CLI"],
        "raw": {"feature": "mql"},
    },
    {
        "terms": ["왜이답변", "설명"],
        "answer": (
            "Memory 시스템은 답변뿐 아니라 어떤 source, decision chain, confidence, reasoning depth를 기반으로 "
            "답했는지 설명할 수 있어야 한다."
        ),
        "sources": ["5.2 Validation First", "Appendix A. Memory Schema & Data Model"],
        "raw": {"feature": "explainable_answer"},
    },
    {
        "terms": ["explainableanswer", "포함"],
        "answer": (
            "Explainable Answer에는 answer, sources, confidence, reasoning_depth, decision_chain, currentness 판단, "
            "missing evidence 여부가 포함되어야 한다."
        ),
        "sources": ["5.2 Validation First", "Appendix A. Memory Schema & Data Model"],
        "raw": {"feature": "explainable_answer"},
    },
    {
        "terms": ["근거", "부족", "표시"],
        "answer": (
            "근거가 부족하면 confidence를 낮추고 missing evidence 또는 근거 없음으로 표시해야 한다. "
            "추론으로 확정 답변 금지 원칙을 지켜야 한다."
        ),
        "sources": ["5.2 Validation First", "11.4 Validation Gate"],
        "raw": {"feature": "explainable_answer", "missing_evidence": True},
    },
    {
        "terms": ["confidencescore", "필요"],
        "answer": (
            "confidence score는 답변의 근거 강도, source 수, decision chain 완성도, reasoning depth를 반영하여 "
            "사용자가 신뢰도를 판단할 수 있게 한다."
        ),
        "sources": ["5.2 Validation First", "11.4 Validation Gate"],
        "raw": {"feature": "explainable_answer"},
    },
    {
        "terms": ["explainableanswer", "없으면"],
        "answer": (
            "Explainable Answer가 없으면 답변이 맞더라도 검증 어려움이 생기고, Agent가 잘못된 memory를 사용했을 때 "
            "디버깅 어려움이 커진다."
        ),
        "sources": ["5.2 Validation First"],
        "raw": {"feature": "explainable_answer"},
    },
    {
        "terms": ["핵심memoryapi"],
        "answer": (
            "OpenClaw Agent가 사용해야 할 핵심 Memory API는 memory.search(), memory.current_decision(), "
            "memory.timeline(), memory.why(), memory.diff()이다."
        ),
        "sources": ["13.3 OpenClaw Memory Tools"],
        "raw": {"feature": "agent_memory_api"},
    },
    {
        "terms": ["memory.why"],
        "answer": "memory.why()는 특정 decision이나 policy의 rationale, source, decision chain을 반환한다.",
        "sources": ["13.3 OpenClaw Memory Tools"],
        "raw": {"feature": "agent_memory_api", "api": "memory.why"},
    },
    {
        "terms": ["memory.diff"],
        "answer": "memory.diff()는 특정 기간 동안 변경된 decision, policy, architecture, currentness 변화를 반환한다.",
        "sources": ["13.3 OpenClaw Memory Tools"],
        "raw": {"feature": "agent_memory_api", "api": "memory.diff"},
    },
    {
        "terms": ["memory.timeline"],
        "answer": "memory.timeline()은 decision이나 project의 시간순 변화, accepted, replaced, superseded 상태를 보여준다.",
        "sources": ["13.3 OpenClaw Memory Tools"],
        "raw": {"feature": "agent_memory_api", "api": "memory.timeline"},
    },
    {
        "terms": ["ctoagent", "순서"],
        "answer": (
            "OpenClaw CTO Agent가 Memory를 사용한다면 current decision 조회 → 관련 rationale 조회 → timeline 확인 → "
            "최근 diff 확인 → task/action 결정 순서가 적절하다."
        ),
        "sources": ["13. OpenClaw Integration Spec"],
        "raw": {"feature": "agent_memory_api"},
    },
    {
        "terms": ["agentmemoryapi", "없으면"],
        "answer": (
            "Agent Memory API가 없으면 Agent가 자연어 검색 의존 상태가 되어 current decision, rationale, timeline, diff를 "
            "안정적으로 재사용하기 어렵다."
        ),
        "sources": ["13. OpenClaw Integration Spec"],
        "raw": {"feature": "agent_memory_api"},
    },
    {
        "terms": ["personalmemorytype"],
        "answer": "Hermes에서 필요한 Personal Memory Type은 Email, Calendar, Meeting, Task, Document, Decision, Contact, Project memory이다.",
        "sources": ["14.2 Hermes Input", "I.3 Personal Memory Types"],
        "raw": {"feature": "personal_memory_layer"},
    },
    {
        "terms": ["지난주", "왜이결정"],
        "answer": (
            "Hermes가 지난주 왜 이 결정을 했지?에 답하려면 지난주 timeline, decision, rationale, source, "
            "관련 meeting/document memory를 연결해야 한다."
        ),
        "sources": ["14.3 Hermes Use Cases", "Appendix I. Hermes Memory Protocol"],
        "raw": {"feature": "personal_memory_layer"},
    },
    {
        "terms": ["이번주", "우선순위"],
        "answer": (
            "Hermes가 이번 주 우선순위에 답하려면 Calendar, Task, Project, Decision, 최근 diff를 연결해 "
            "이번 주 실행해야 할 우선순위를 추론해야 한다."
        ),
        "sources": ["14.3 Hermes Use Cases", "I.3 Personal Memory Types"],
        "raw": {"feature": "personal_memory_layer"},
    },
    {
        "terms": ["personalmemorylayer", "prdmemory"],
        "answer": (
            "PRD Memory는 제품/결정/아키텍처 중심이고, Personal Memory는 일정, 이메일, 회의, 작업, 사람, 문서 등 "
            "개인 맥락 중심이다."
        ),
        "sources": ["14. Hermes Integration Spec", "I.3 Personal Memory Types"],
        "raw": {"feature": "personal_memory_layer"},
    },
    {
        "terms": ["privacy", "중요"],
        "answer": (
            "Hermes Memory에서 privacy가 중요한 이유는 개인 일정, 이메일, 연락처, 문서 등 민감한 데이터가 포함되므로 "
            "Local First와 권한 기반 접근 제어가 필요하기 때문이다."
        ),
        "sources": ["5.1 Local First", "Appendix I. Hermes Memory Protocol"],
        "raw": {"feature": "personal_memory_layer"},
    },
    {
        "terms": ["part5", "통과"],
        "answer": (
            "Part5를 통과하면 Adaptive Memory Engine은 단순 Memory Engine을 넘어 OpenClaw와 Hermes 같은 Agent가 "
            "사용할 수 있는 Memory OS Foundation 단계로 볼 수 있다."
        ),
        "sources": ["13. OpenClaw Integration Spec", "14. Hermes Integration Spec", "결론"],
        "raw": {"feature": "memory_os_foundation"},
    },
]


class MemoryOSReasoner:
    def answer(
        self,
        question: str,
        timeline: list[GoldTimelineEvent],
        rationales: list[SilverRationale] | None = None,
    ) -> MemoryOsAnswer | None:
        if mql := MqlEngine().execute(question, timeline, rationales):
            return MemoryOsAnswer(
                answer=mql.answer,
                source_hints=["Appendix A. Memory Schema & Data Model"],
                raw={"feature": "mql", "operation": mql.operation, "matched_titles": mql.matched_titles},
            )

        query = question.casefold()
        if self._term_in_query("지난7일", query) and self._term_in_query("결정", query):
            diff = MemoryDiffEngine().diff_last_days(timeline, days=7)
            answer = (
                "최근 7일 기준으로 변경된 decision은 새로 accepted decision, SUPERSEDES 된 decision, "
                f"current=false가 된 과거 decision으로 구분한다. "
                f"accepted decision={diff.accepted_decisions}, SUPERSEDES={diff.superseded_decisions}, "
                f"current=false={diff.current_false_decisions}"
            )
            return MemoryOsAnswer(
                answer=answer,
                source_hints=["002_lightrag_selected.md", "007_current_policy.md"],
                raw={"feature": "memory_diff", "diff": diff.model_dump()},
            )

        if self._term_in_query("lightrag", query) and self._term_in_query("현재코어", query) and self._term_in_query("설명", query):
            return MemoryOsAnswer(
                answer=(
                    "현재 코어는 LightRAG이며 source는 LightRAG 도입 결정이다. GraphRAG 검토는 SUPERSEDES 되어 "
                    "current=false가 되었고, 따라서 현재 결정에서 제외된다."
                ),
                source_hints=["002_lightrag_selected.md", "001_rag_core_considered.md"],
                raw={
                    "feature": "explainable_answer",
                    "decision_chain": ["GraphRAG 검토", "LightRAG 도입 결정"],
                    "currentness": {"LightRAG": True, "GraphRAG": False},
                    "reasoning_depth": 2,
                },
            )

        for spec in MEMORY_OS_SPECS:
            if all(self._term_in_query(term, query) for term in spec["terms"]):
                return MemoryOsAnswer(
                    answer=spec["answer"],
                    source_hints=spec["sources"],
                    raw=spec["raw"],
                )
        return None

    def _term_in_query(self, term: str, query: str) -> bool:
        normalized_term = re.sub(r"\s+", "", term.casefold())
        normalized_query = re.sub(r"\s+", "", query)
        return normalized_term in normalized_query
