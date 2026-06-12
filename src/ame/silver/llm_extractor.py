from __future__ import annotations

import hashlib
from typing import Literal, Protocol

from pydantic import BaseModel, Field, ValidationError

from ame.bronze.schema import BronzeDocument
from ame.core.errors import LlmClientError
from ame.silver.extractor import DeterministicExtractor
from ame.silver.prompts import MEMORY_EXTRACTION_PROMPT
from ame.silver.schema import SilverDecision, SilverEntity, SilverRelation


class LlmClient(Protocol):
    def complete_json(self, prompt: str, payload: dict) -> dict:
        ...


class RawLlmEntity(BaseModel):
    type: Literal["Person", "Project", "Tool", "Concept", "Decision", "Issue", "Action"]
    name: str
    span: str | None = None
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)


class RawLlmRelation(BaseModel):
    subject: str
    predicate: Literal["USES", "MADE_IN", "RELATED_TO", "SUPERSEDES", "MENTIONS"]
    object: str
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class RawLlmDecision(BaseModel):
    title: str
    status: Literal["proposed", "accepted", "rejected", "superseded"] = "proposed"
    project: str | None = None
    rationale: str | None = None
    decision_date: str | None = None
    participants: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class RawLlmExtraction(BaseModel):
    entities: list[RawLlmEntity] = Field(default_factory=list)
    relations: list[RawLlmRelation] = Field(default_factory=list)
    decisions: list[RawLlmDecision] = Field(default_factory=list)


class LlmExtractor:
    """Local LLM extraction with rule-based prefill for stable metadata."""

    def __init__(self, client: LlmClient | None = None, max_retries: int = 1):
        self.client = client
        self.max_retries = max_retries
        self.fallback = DeterministicExtractor()

    def extract(self, doc: BronzeDocument) -> tuple[list[SilverEntity], list[SilverRelation], list[SilverDecision]]:
        if self.client is None:
            return self.fallback.extract(doc)
        baseline_entities, baseline_relations, baseline_decisions = self.fallback.extract(doc)
        payload = {
            "source_id": doc.source_id,
            "metadata": doc.metadata,
            "content": doc.content,
        }
        raw = self._complete_extraction(payload)
        entities = baseline_entities + self._entities(doc, raw.entities)
        relations = baseline_relations + self._relations(doc, raw.relations)
        decisions = baseline_decisions + self._decisions(doc, raw.decisions)
        return self._dedupe_entities(entities), self._dedupe_relations(relations), self._dedupe_decisions(decisions)

    def _complete_extraction(self, payload: dict) -> RawLlmExtraction:
        assert self.client is not None
        retry_payload = dict(payload)
        last_error: str | None = None
        last_raw: dict | None = None
        for attempt in range(self.max_retries + 1):
            if last_error:
                retry_payload["retry_feedback"] = (
                    "Previous response failed schema validation. Return only the requested JSON object. "
                    f"Validation error: {last_error[:500]}"
                )
            raw = self.client.complete_json(MEMORY_EXTRACTION_PROMPT, retry_payload)
            last_raw = raw
            try:
                return RawLlmExtraction.model_validate(raw)
            except ValidationError as exc:
                last_error = str(exc)
                if attempt >= self.max_retries:
                    return self._best_effort_extraction(last_raw)
        raise LlmClientError("LLM extraction schema validation failed.")

    def _best_effort_extraction(self, raw: dict | None) -> RawLlmExtraction:
        if not isinstance(raw, dict):
            raise LlmClientError("LLM extraction schema validation failed.")
        return RawLlmExtraction(
            entities=self._valid_rows(raw.get("entities"), RawLlmEntity),
            relations=self._valid_rows(raw.get("relations"), RawLlmRelation),
            decisions=self._valid_rows(raw.get("decisions"), RawLlmDecision),
        )

    def _valid_rows(self, rows: object, model: type[BaseModel]) -> list:
        if not isinstance(rows, list):
            return []
        valid = []
        for row in rows:
            try:
                valid.append(model.model_validate(row))
            except ValidationError:
                continue
        return valid

    def _entities(self, doc: BronzeDocument, rows: list[RawLlmEntity]) -> list[SilverEntity]:
        entities: list[SilverEntity] = []
        for row in rows:
            name = row.name.strip()
            entity_type = row.type
            span = (row.span or name).strip()
            entities.append(
                SilverEntity(
                    id=self._id("entity", doc.id, entity_type, name),
                    corpus_id=doc.corpus_id,
                    type=entity_type,
                    name=name,
                    span=span,
                    source_ids=[doc.id],
                    confidence=row.confidence,
                )
            )
        return entities

    def _relations(self, doc: BronzeDocument, rows: list[RawLlmRelation]) -> list[SilverRelation]:
        relations: list[SilverRelation] = []
        for row in rows:
            relations.append(
                SilverRelation(
                    id=self._id("relation", doc.id, row.subject, row.predicate, row.object),
                    corpus_id=doc.corpus_id,
                    subject=row.subject.strip(),
                    predicate=row.predicate,
                    object=row.object.strip(),
                    source_ids=[doc.id],
                    confidence=row.confidence,
                )
            )
        return relations

    def _decisions(self, doc: BronzeDocument, rows: list[RawLlmDecision]) -> list[SilverDecision]:
        decisions: list[SilverDecision] = []
        for row in rows:
            decisions.append(
                SilverDecision(
                    id=self._id("decision", doc.id, row.title),
                    corpus_id=doc.corpus_id,
                    title=row.title.strip(),
                    status=row.status,
                    project=row.project,
                    rationale=row.rationale,
                    decision_date=row.decision_date or doc.metadata.get("frontmatter", {}).get("date"),
                    participants=row.participants,
                    source_ids=[doc.id],
                    confidence=row.confidence,
                )
            )
        return decisions

    def _dedupe_entities(self, entities: list[SilverEntity]) -> list[SilverEntity]:
        seen: set[tuple[str, str]] = set()
        deduped: list[SilverEntity] = []
        for entity in entities:
            key = (entity.type, entity.name.casefold())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(entity)
        return deduped

    def _dedupe_relations(self, relations: list[SilverRelation]) -> list[SilverRelation]:
        seen: set[tuple[str, str, str]] = set()
        deduped: list[SilverRelation] = []
        for relation in relations:
            key = (relation.subject.casefold(), relation.predicate, relation.object.casefold())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(relation)
        return deduped

    def _dedupe_decisions(self, decisions: list[SilverDecision]) -> list[SilverDecision]:
        seen: set[str] = set()
        deduped: list[SilverDecision] = []
        for decision in decisions:
            key = decision.title.casefold()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(decision)
        return deduped

    def _id(self, prefix: str, *parts: str) -> str:
        digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
        return f"{prefix}_{digest}"
