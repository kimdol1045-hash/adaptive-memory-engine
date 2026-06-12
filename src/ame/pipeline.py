from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from ame.bronze.store import BronzeStore
from ame.connectors.router import ConnectorRouter
from ame.core.config import load_config
from ame.core.corpus import require_corpus
from ame.core.state import CorpusStateStore, IngestedDocumentState
from ame.gold.builder import GoldBuilder
from ame.gold.store import GoldStore
from ame.hardware.profiler import HardwareProfiler
from ame.models.ollama import OllamaClient
from ame.models.registry import load_default_registry
from ame.models.router import ModelRouter
from ame.silver.extractor import DeterministicExtractor
from ame.silver.llm_extractor import LlmClient, LlmExtractor
from ame.silver.rationale import RationaleExtractor
from ame.silver.schema import SilverEntity
from ame.silver.store import SilverStore
from ame.storage.lightrag_adapter import LightRagAdapter
from ame.validation.confidence import passes_confidence
from ame.validation.grounding import is_grounded
from ame.validation.type_gate import relation_type_valid


class IngestReport(BaseModel):
    mode: str
    documents: int
    silver_entities: int
    silver_relations: int
    silver_decisions: int
    silver_rationales: int
    rejected: int
    gold_nodes: int
    gold_edges: int
    custom_kg_path: Path


class MemoryPipeline:
    def ingest(
        self,
        corpus_id: str,
        source_path: Path,
        mode: Literal["deterministic", "llm"] = "llm",
        llm_client: LlmClient | None = None,
        profile: str | None = None,
    ) -> IngestReport:
        root = require_corpus(corpus_id)
        config = load_config()
        connector = ConnectorRouter().resolve(source_path, profile)
        bronze = BronzeStore(root)
        extractor = DeterministicExtractor() if mode == "deterministic" else LlmExtractor(llm_client or self._default_llm_client(config))

        docs_by_id = {}
        for ref in connector.scan(source_path):
            doc = bronze.put(connector.load(corpus_id, ref))
            docs_by_id[doc.id] = doc
        current_docs = list(docs_by_id.values())
        all_docs = list(bronze.list())
        doc_map = {doc.id: doc for doc in current_docs}
        current_doc_ids = set(docs_by_id)
        silver = SilverStore(root)
        entities = [row for row in silver.entities() if not _row_uses_sources(row, current_doc_ids)]
        relations = [row for row in silver.relations() if not _row_uses_sources(row, current_doc_ids)]
        decisions = [row for row in silver.decisions() if not _row_uses_sources(row, current_doc_ids)]
        existing_rationales = [row for row in silver.rationales() if not _row_uses_sources(row, current_doc_ids)]
        rejected: list[dict] = [
            row for row in _existing_rejected(root) if not _rejected_uses_sources(row, current_doc_ids)
        ]
        new_decisions = []

        for doc in current_docs:
            extracted_entities, extracted_relations, extracted_decisions = extractor.extract(doc)
            valid_entities = []
            for entity in extracted_entities:
                if not is_grounded(entity, doc_map) or not passes_confidence(entity.confidence, config.engine.confidence_threshold):
                    rejected.append({"kind": "entity", "id": entity.id, "reason": "validation_failed"})
                    continue
                valid_entities.append(entity)
            valid_decisions = []
            for decision in extracted_decisions:
                if not passes_confidence(decision.confidence, config.engine.confidence_threshold):
                    rejected.append({"kind": "decision", "id": decision.id, "reason": "validation_failed"})
                    continue
                valid_decisions.append(decision)
            decision_entities = [
                SilverEntity(
                    id=f"entity_{decision.id}",
                    corpus_id=decision.corpus_id,
                    type="Decision",
                    name=decision.title,
                    span=decision.title if decision.title in doc.content else None,
                    source_ids=decision.source_ids,
                    confidence=decision.confidence,
                )
                for decision in valid_decisions
            ]
            validation_entities = valid_entities + decision_entities
            for relation in extracted_relations:
                if not passes_confidence(relation.confidence, config.engine.confidence_threshold) or not relation_type_valid(relation, validation_entities):
                    rejected.append(
                        {
                            "kind": "relation",
                            "id": relation.id,
                            "reason": "validation_failed",
                            "subject": relation.subject,
                            "predicate": relation.predicate,
                            "object": relation.object,
                        }
                    )
                    continue
                relations.append(relation)
            entities.extend(valid_entities)
            decisions.extend(valid_decisions)
            new_decisions.extend(valid_decisions)

        rationales = existing_rationales + RationaleExtractor().extract(current_docs, new_decisions)
        silver.replace(entities, relations, decisions, rejected, rationales)
        nodes, edges, timeline = GoldBuilder().build(entities, relations, decisions, rationales)
        GoldStore(root).replace(nodes, edges, timeline)
        kg_path = LightRagAdapter(root).sync(nodes, edges, current_docs)
        counts = {
            "documents": len(all_docs),
            "silver_entities": len(entities),
            "silver_relations": len(relations),
            "silver_decisions": len(decisions),
            "silver_rationales": len(rationales),
            "rejected": len(rejected),
            "gold_nodes": len(nodes),
            "gold_edges": len(edges),
        }
        CorpusStateStore(root).record_ingest(
            source_path=source_path,
            mode=mode,
            documents=[
                IngestedDocumentState(id=doc.id, source_id=doc.source_id, content_hash=doc.content_hash)
                for doc in all_docs
            ],
            counts=counts,
        )

        return IngestReport(
            mode=mode,
            documents=len(all_docs),
            silver_entities=len(entities),
            silver_relations=len(relations),
            silver_decisions=len(decisions),
            silver_rationales=len(rationales),
            rejected=len(rejected),
            gold_nodes=len(nodes),
            gold_edges=len(edges),
            custom_kg_path=kg_path,
        )

    def _default_llm_client(self, config) -> OllamaClient:
        registry = load_default_registry()
        profile = HardwareProfiler().profile(Path.home())
        plan = ModelRouter(registry).plan(profile)
        return OllamaClient(model=plan.models.extract.model, base_url=config.lightrag.ollama_host)


def _row_uses_sources(row, source_ids: set[str]) -> bool:
    return bool(set(getattr(row, "source_ids", []) or []) & source_ids)


def _existing_rejected(root: Path) -> list[dict]:
    path = root / "silver" / "rejected.jsonl"
    if not path.exists():
        return []
    import json

    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _rejected_uses_sources(row: dict, source_ids: set[str]) -> bool:
    values = set()
    for key in ["source_id", "source_ids", "id", "subject", "object"]:
        value = row.get(key)
        if isinstance(value, str):
            values.add(value)
        elif isinstance(value, list):
            values.update(str(item) for item in value)
    return bool(values & source_ids)
