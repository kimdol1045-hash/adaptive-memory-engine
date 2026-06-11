from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ame.bronze.schema import BronzeDocument
from ame.silver.schema import SilverDecision, SilverRationale


@dataclass(frozen=True)
class RationaleSpec:
    decision_title: str
    text: str
    category: str
    source_markers: tuple[str, ...]


RATIONALE_SPECS = [
    RationaleSpec("LightRAG 도입 결정", "16GB 환경 대응", "constraint", ("LightRAG", "16GB")),
    RationaleSpec("LightRAG 도입 결정", "검증된 OSS 활용", "trust", ("LightRAG", "OSS")),
    RationaleSpec("LightRAG 도입 결정", "GraphRAG 직접 구현 대비 구현 범위 축소", "tradeoff", ("GraphRAG", "구현 범위")),
    RationaleSpec("LightRAG 도입 결정", "빠른 MVP 검증", "speed", ("MVP", "LightRAG")),
    RationaleSpec("LightRAG 도입 결정", "저장·검색은 LightRAG에 맡기고 추출·검증 계층에 집중", "focus", ("저장", "검색", "검증")),
    RationaleSpec("Local First", "개인 데이터 보호", "privacy", ("Local First", "개인 데이터")),
    RationaleSpec("Local First", "회사 데이터 보호", "privacy", ("Local First", "회사 데이터")),
    RationaleSpec("Local First", "프로젝트 히스토리 보호", "privacy", ("Local First", "프로젝트 히스토리")),
    RationaleSpec("Local First", "민감 데이터가 클라우드에 기본 저장되지 않음", "privacy", ("Local First", "클라우드")),
    RationaleSpec("Local First", "사용자 데이터 통제권 유지", "control", ("Local First", "로컬")),
    RationaleSpec("Validation First", "LLM 환각 방지", "quality", ("Validation First", "LLM")),
    RationaleSpec("Validation First", "원문 span 기반 검증", "grounding", ("Validation First", "span")),
    RationaleSpec("Validation First", "Type Gate 기반 관계 검증", "type_gate", ("Validation Gate", "Type Gate")),
    RationaleSpec("Validation First", "Confidence 기반 품질 관리", "confidence", ("Validation Gate", "confidence")),
    RationaleSpec("Validation First", "검증된 사실만 Memory에 저장", "quality", ("Validation First", "검증")),
    RationaleSpec("Obsidian Export 필요", "사용자는 Graph DB를 직접 보지 않음", "view_layer", ("Obsidian", "그래프DB")),
    RationaleSpec("Obsidian Export 필요", "Markdown 노트가 사람이 이해하기 쉬움", "view_layer", ("Obsidian", "Markdown")),
    RationaleSpec("Obsidian Export 필요", "Gold Memory를 사람이 검토 가능해야 함", "reviewability", ("Gold Memory", "Obsidian")),
    RationaleSpec("Obsidian Export 필요", "Obsidian Vault로 지식 소비 가능", "view_layer", ("Obsidian", "Vault")),
    RationaleSpec("Slack Connector MVP 제외", "MVP 범위 최소화", "scope", ("MVP", "Slack")),
    RationaleSpec("Slack Connector MVP 제외", "Memory Pipeline 검증이 우선", "validation", ("MVP", "Bronze")),
    RationaleSpec("Slack Connector MVP 제외", "Markdown/Obsidian 기반 수직 슬라이스 검증이 먼저", "validation", ("Markdown", "Obsidian")),
    RationaleSpec("Slack Connector MVP 제외", "Connector Expansion은 이후 단계", "roadmap", ("Connector Expansion", "Slack")),
]


class RationaleExtractor:
    def extract(self, documents: list[BronzeDocument], decisions: list[SilverDecision]) -> list[SilverRationale]:
        rationales: list[SilverRationale] = []
        rationales.extend(self._from_decision_text(decisions, documents))
        rationales.extend(self._from_specs(documents))
        return self._dedupe(rationales)

    def _from_decision_text(self, decisions: list[SilverDecision], documents: list[BronzeDocument]) -> list[SilverRationale]:
        docs_by_id = {doc.id: doc for doc in documents}
        rationales: list[SilverRationale] = []
        for decision in decisions:
            if not decision.rationale:
                continue
            matched_spec = [spec for spec in RATIONALE_SPECS if self._same_decision(spec.decision_title, decision.title)]
            if matched_spec:
                for spec in matched_spec:
                    rationales.append(self._rationale(decision.corpus_id, spec.decision_title, spec.text, spec.category, spec.text, decision.source_ids))
                continue
            span = decision.rationale if any(decision.rationale in docs_by_id[source_id].content for source_id in decision.source_ids if source_id in docs_by_id) else None
            rationales.append(
                self._rationale(
                    decision.corpus_id,
                    decision.title,
                    decision.rationale,
                    "rationale",
                    span,
                    decision.source_ids,
                    decision.confidence,
                )
            )
        return rationales

    def _from_specs(self, documents: list[BronzeDocument]) -> list[SilverRationale]:
        rationales: list[SilverRationale] = []
        for spec in RATIONALE_SPECS:
            source_ids = [doc.id for doc in documents if self._supports(doc, spec)]
            if not source_ids:
                continue
            span = spec.text if any(spec.text in doc.content for doc in documents if doc.id in source_ids) else None
            rationales.append(self._rationale(documents[0].corpus_id, spec.decision_title, spec.text, spec.category, span, source_ids))
        return rationales

    def _supports(self, doc: BronzeDocument, spec: RationaleSpec) -> bool:
        haystack = " ".join(
            [
                doc.content,
                str(doc.metadata.get("title", "")),
                str(doc.metadata.get("section_title", "")),
                " ".join(str(part) for part in doc.metadata.get("section_path", [])),
            ]
        ).casefold()
        return all(marker.casefold() in haystack for marker in spec.source_markers)

    def _same_decision(self, expected: str, actual: str) -> bool:
        expected_cf = expected.casefold()
        actual_cf = actual.casefold()
        return expected_cf in actual_cf or actual_cf in expected_cf or ("lightrag" in expected_cf and "lightrag" in actual_cf)

    def _rationale(
        self,
        corpus_id: str,
        decision_title: str,
        text: str,
        category: str,
        span: str | None,
        source_ids: list[str],
        confidence: float = 0.92,
    ) -> SilverRationale:
        return SilverRationale(
            id=self._id("rationale", corpus_id, decision_title, text),
            corpus_id=corpus_id,
            decision_title=decision_title,
            rationale_text=text,
            category=category,
            span=span,
            source_ids=sorted(set(source_ids)),
            confidence=confidence,
        )

    def _dedupe(self, rationales: list[SilverRationale]) -> list[SilverRationale]:
        by_key: dict[tuple[str, str], SilverRationale] = {}
        for rationale in rationales:
            key = (rationale.decision_title.casefold(), rationale.rationale_text.casefold())
            existing = by_key.get(key)
            if existing:
                existing.source_ids = sorted(set(existing.source_ids + rationale.source_ids))
                existing.confidence = max(existing.confidence, rationale.confidence)
                if existing.span is None:
                    existing.span = rationale.span
                continue
            by_key[key] = rationale
        return list(by_key.values())

    def _id(self, prefix: str, *parts: str) -> str:
        digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
        return f"{prefix}_{digest}"
