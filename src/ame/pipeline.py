from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel

from ame.bronze.store import BronzeStore
from ame.connectors.router import ConnectorRouter
from ame.core.config import load_config
from ame.core.corpus import require_corpus
from ame.core.state import CorpusStateStore, IngestedDocumentState
from ame.gold.builder import GoldBuilder
from ame.gold.store import GoldStore
from ame.models.ollama import OllamaClient
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


ProgressCallback = Callable[[dict], None]


class MemoryPipeline:
    def ingest(
        self,
        corpus_id: str,
        source_path: Path,
        mode: Literal["deterministic", "llm"] = "llm",
        llm_client: LlmClient | None = None,
        profile: str | None = None,
        progress: ProgressCallback | None = None,
    ) -> IngestReport:
        root = require_corpus(corpus_id)
        transaction = _IngestTransaction(root)
        staging_root = transaction.stage()
        try:
            _emit(progress, stage="staging", message="Created transactional ingest staging directory.", staging_root=str(staging_root))
            report = self._ingest_into(
                staging_root,
                corpus_id,
                source_path,
                mode=mode,
                llm_client=llm_client,
                profile=profile,
                progress=progress,
            )
            _emit(progress, stage="commit", message="Committing staged memory build.")
            transaction.commit(staging_root)
            _emit(progress, stage="completed", message="Memory build committed.")
            return report.model_copy(update={"custom_kg_path": root / "store" / "lightrag" / "custom_kg.json"})
        except Exception:
            transaction.rollback(staging_root)
            _emit(progress, stage="rolled_back", message="Memory build failed and staged artifacts were removed.")
            raise

    def _ingest_into(
        self,
        root: Path,
        corpus_id: str,
        source_path: Path,
        *,
        mode: Literal["deterministic", "llm"],
        llm_client: LlmClient | None,
        profile: str | None,
        progress: ProgressCallback | None,
    ) -> IngestReport:
        config = load_config()
        connector = ConnectorRouter().resolve(source_path, profile)
        bronze = BronzeStore(root)
        extractor = DeterministicExtractor() if mode == "deterministic" else LlmExtractor(llm_client or self._default_llm_client(config))

        refs = connector.scan(source_path)
        _emit(
            progress,
            stage="bronze",
            current=0,
            total=len(refs),
            message="Scanning source documents and writing Bronze chunks.",
        )
        incoming_docs = [connector.load(corpus_id, ref) for ref in refs]
        incoming_source_roots = {_doc_root_source_id(doc) for doc in incoming_docs}
        stale_docs = [doc for doc in bronze.list() if _doc_root_source_id(doc) in incoming_source_roots]
        stale_doc_ids = {doc.id for doc in stale_docs}
        if stale_doc_ids:
            bronze.mark_inactive(stale_doc_ids)
            _emit(
                progress,
                stage="bronze",
                current=0,
                total=len(refs),
                replaced_documents=len(stale_doc_ids),
                message="Marked previous Bronze chunks as inactive for updated source files.",
            )
        docs_by_id = {}
        for index, (ref, incoming_doc) in enumerate(zip(refs, incoming_docs, strict=True), start=1):
            doc = bronze.put(incoming_doc)
            bronze.mark_active([doc.id])
            docs_by_id[doc.id] = doc
            _emit(
                progress,
                stage="bronze",
                current=index,
                total=len(refs),
                source_id=ref.source_id,
                message="Bronze chunk stored.",
            )
        current_docs = list(docs_by_id.values())
        all_docs = list(bronze.list())
        doc_map = {doc.id: doc for doc in current_docs}
        current_doc_ids = set(docs_by_id) | stale_doc_ids
        silver = SilverStore(root)
        existing_entities = silver.entities()
        existing_relations = silver.relations()
        existing_decisions = silver.decisions()
        existing_rationales_all = silver.rationales()
        existing_rejected = _existing_rejected(root)
        if stale_doc_ids:
            _archive_source_update(
                root,
                corpus_id=corpus_id,
                source_roots=incoming_source_roots,
                previous_docs=stale_docs,
                current_docs=current_docs,
                entities=[row for row in existing_entities if _row_uses_sources(row, stale_doc_ids)],
                relations=[row for row in existing_relations if _row_uses_sources(row, stale_doc_ids)],
                decisions=[row for row in existing_decisions if _row_uses_sources(row, stale_doc_ids)],
                rationales=[row for row in existing_rationales_all if _row_uses_sources(row, stale_doc_ids)],
                rejected=[row for row in existing_rejected if _rejected_uses_sources(row, stale_doc_ids)],
            )
        entities = [row for row in existing_entities if not _row_uses_sources(row, current_doc_ids)]
        relations = [row for row in existing_relations if not _row_uses_sources(row, current_doc_ids)]
        decisions = [row for row in existing_decisions if not _row_uses_sources(row, current_doc_ids)]
        existing_rationales = [row for row in existing_rationales_all if not _row_uses_sources(row, current_doc_ids)]
        rejected: list[dict] = [
            row for row in _existing_rejected(root) if not _rejected_uses_sources(row, current_doc_ids)
        ]
        new_decisions = []

        for index, doc in enumerate(current_docs, start=1):
            _emit(
                progress,
                stage="silver_extraction",
                current=index,
                total=len(current_docs),
                source_id=doc.source_id,
                chars=len(doc.content),
                message="Extracting Silver entities, relations, and decisions with local LLM.",
            )
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
            _emit(
                progress,
                stage="silver_extraction",
                current=index,
                total=len(current_docs),
                source_id=doc.source_id,
                entities=len(entities),
                relations=len(relations),
                decisions=len(decisions),
                rejected=len(rejected),
                message="Silver extraction chunk completed.",
            )

        _emit(progress, stage="rationale", message="Extracting rationale memory from accepted decisions.")
        rationales = existing_rationales + RationaleExtractor().extract(current_docs, new_decisions)
        silver.replace(entities, relations, decisions, rejected, rationales)
        _emit(progress, stage="gold", message="Building Gold graph and timeline.")
        nodes, edges, timeline = GoldBuilder().build(entities, relations, decisions, rationales)
        GoldStore(root).replace(nodes, edges, timeline)
        _emit(progress, stage="lightrag", message="Syncing Gold graph and Bronze chunks into LightRAG custom KG.")
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
        CorpusStateStore(root, corpus_id=corpus_id).record_ingest(
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
        return OllamaClient(model=config.lightrag.llm_model, base_url=config.lightrag.ollama_host)


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


def _doc_root_source_id(doc) -> str:
    root = doc.metadata.get("root_source_id") or doc.metadata.get("source_file")
    if isinstance(root, str) and root:
        return root
    return str(doc.source_id).split("#", 1)[0]


def _archive_source_update(
    root: Path,
    *,
    corpus_id: str,
    source_roots: set[str],
    previous_docs: list,
    current_docs: list,
    entities: list,
    relations: list,
    decisions: list,
    rationales: list,
    rejected: list[dict],
) -> None:
    if not previous_docs:
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    history_root = root / "history" / "source_updates"
    history_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "corpus_id": corpus_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_roots": sorted(source_roots),
        "previous_bronze_docs": [_doc_history(doc) for doc in previous_docs],
        "current_bronze_docs": [_doc_history(doc) for doc in current_docs],
        "archived_silver": {
            "entities": [_dump_model(row) for row in entities],
            "relations": [_dump_model(row) for row in relations],
            "decisions": [_dump_model(row) for row in decisions],
            "rationales": [_dump_model(row) for row in rationales],
            "rejected": rejected,
        },
        "gold_snapshot": _snapshot_gold(root, timestamp),
    }
    (history_root / f"{timestamp}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _doc_history(doc) -> dict:
    return {
        "id": doc.id,
        "source_id": doc.source_id,
        "content_hash": doc.content_hash,
        "active": doc.metadata.get("active", True),
        "created_at": doc.created_at,
    }


def _dump_model(row) -> dict:
    if hasattr(row, "model_dump"):
        return row.model_dump(mode="json")
    return dict(row)


def _snapshot_gold(root: Path, timestamp: str) -> str | None:
    source = root / "gold"
    if not source.exists() or not any(source.iterdir()):
        return None
    target = root / "history" / "gold_snapshots" / timestamp
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, dirs_exist_ok=True)
    return str(target)


def _emit(callback: ProgressCallback | None, **event) -> None:
    if callback is not None:
        callback(event)


class _IngestTransaction:
    def __init__(self, root: Path):
        self.root = root
        self.stage_root = root.parent / f".{root.name}.ingest-{uuid4().hex}"

    def stage(self) -> Path:
        if self.stage_root.exists():
            shutil.rmtree(self.stage_root)
        if self.root.exists():
            shutil.copytree(self.root, self.stage_root)
        else:
            self.stage_root.mkdir(parents=True, exist_ok=True)
        return self.stage_root

    def commit(self, staging_root: Path) -> None:
        backup = self.root.parent / f".{self.root.name}.backup-{uuid4().hex}"
        if self.root.exists():
            self.root.replace(backup)
        staging_root.replace(self.root)
        if backup.exists():
            shutil.rmtree(backup)

    def rollback(self, staging_root: Path) -> None:
        if staging_root.exists():
            shutil.rmtree(staging_root)
