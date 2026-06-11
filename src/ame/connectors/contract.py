from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from ame.bronze.schema import BronzeDocument
from ame.bronze.store import BronzeStore
from ame.connectors.base import Connector, SourceRef
from ame.connectors.sync_history import ConnectorSyncStore
from ame.core.corpus import require_corpus


class ConnectorProfile(BaseModel):
    name: str
    source_type: str
    mode: Literal["export", "live"] = "export"
    version: str = "1"
    features: list[str] = Field(default_factory=list)
    contract: list[str] = Field(
        default_factory=lambda: ["connect", "fetch", "normalize_to_bronze", "diff", "sync"]
    )


class ConnectorConnection(BaseModel):
    profile: ConnectorProfile
    path: Path
    connected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConnectorDiff(BaseModel):
    connector: str
    source_type: str
    source_path: Path
    fetched: int
    new: list[str] = Field(default_factory=list)
    changed: list[str] = Field(default_factory=list)
    unchanged: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        return {
            "fetched": self.fetched,
            "new": len(self.new),
            "changed": len(self.changed),
            "unchanged": len(self.unchanged),
            "removed": len(self.removed),
        }


class ConnectorContractSyncReport(BaseModel):
    corpus_id: str
    connector: str
    source_type: str
    source_path: Path
    fetched: int
    new: int
    changed: int
    unchanged: int
    removed: int
    ingested_documents: int
    sync_run_id: str | None = None


class ContractConnector(Protocol):
    profile: ConnectorProfile

    def connect(self, path: Path) -> ConnectorConnection:
        ...

    def fetch(self, path: Path) -> list[SourceRef]:
        ...

    def normalize_to_bronze(self, corpus_id: str, ref: SourceRef) -> BronzeDocument:
        ...

    def diff(self, corpus_id: str, path: Path) -> ConnectorDiff:
        ...

    def sync(self, corpus_id: str, path: Path) -> ConnectorContractSyncReport:
        ...


class ExportConnectorRuntime:
    def __init__(self, connector: Connector, profile: ConnectorProfile):
        self.connector = connector
        self.profile = profile

    def connect(self, path: Path) -> ConnectorConnection:
        return ConnectorConnection(profile=self.profile, path=path.expanduser().resolve())

    def fetch(self, path: Path) -> list[SourceRef]:
        return self.connector.scan(path)

    def normalize_to_bronze(self, corpus_id: str, ref: SourceRef) -> BronzeDocument:
        return self.connector.load(corpus_id, ref)

    def diff(self, corpus_id: str, path: Path) -> ConnectorDiff:
        corpus_root = require_corpus(corpus_id)
        refs = self.fetch(path)
        fetched_docs = [self.normalize_to_bronze(corpus_id, ref) for ref in refs]
        existing_docs = [doc for doc in BronzeStore(corpus_root).list() if doc.source_type == self.connector.source_type]
        existing_by_source = {doc.source_id: doc for doc in existing_docs}
        fetched_source_ids = {doc.source_id for doc in fetched_docs}

        new: list[str] = []
        changed: list[str] = []
        unchanged: list[str] = []
        for doc in fetched_docs:
            existing = existing_by_source.get(doc.source_id)
            if existing is None:
                new.append(doc.source_id)
            elif existing.content_hash == doc.content_hash:
                unchanged.append(doc.source_id)
            else:
                changed.append(doc.source_id)

        removed = sorted(doc.source_id for doc in existing_docs if doc.source_id not in fetched_source_ids)
        return ConnectorDiff(
            connector=self.profile.name,
            source_type=self.connector.source_type,
            source_path=path,
            fetched=len(refs),
            new=sorted(new),
            changed=sorted(changed),
            unchanged=sorted(unchanged),
            removed=removed,
        )

    def sync(self, corpus_id: str, path: Path) -> ConnectorContractSyncReport:
        corpus_root = require_corpus(corpus_id)
        started_at = datetime.now(timezone.utc)
        sync_store = ConnectorSyncStore(corpus_root)
        diff = self.diff(corpus_id, path)
        ingested = 0
        try:
            from ame.pipeline import MemoryPipeline

            ingest_report = MemoryPipeline().ingest(corpus_id, path, profile=self.profile.name)
            ingested = ingest_report.documents
            run = sync_store.record(
                connector=self.profile.name,
                status="success",
                started_at=started_at,
                source=str(path),
                counts={
                    "fetched": diff.fetched,
                    "new": len(diff.new),
                    "changed": len(diff.changed),
                    "unchanged": len(diff.unchanged),
                    "removed": len(diff.removed),
                    "ingested_documents": ingested,
                },
                metadata={"source_type": self.connector.source_type, "profile": self.profile.name},
            )
            return self._report(corpus_id, path, diff, ingested, run.id)
        except Exception as exc:
            sync_store.record(
                connector=self.profile.name,
                status="failed",
                started_at=started_at,
                source=str(path),
                counts={
                    "fetched": diff.fetched,
                    "new": len(diff.new),
                    "changed": len(diff.changed),
                    "unchanged": len(diff.unchanged),
                    "removed": len(diff.removed),
                    "ingested_documents": ingested,
                },
                metadata={"source_type": self.connector.source_type, "profile": self.profile.name},
                error=str(exc),
            )
            raise

    def _report(
        self,
        corpus_id: str,
        path: Path,
        diff: ConnectorDiff,
        ingested_documents: int,
        sync_run_id: str,
    ) -> ConnectorContractSyncReport:
        return ConnectorContractSyncReport(
            corpus_id=corpus_id,
            connector=self.profile.name,
            source_type=self.connector.source_type,
            source_path=path,
            fetched=diff.fetched,
            new=len(diff.new),
            changed=len(diff.changed),
            unchanged=len(diff.unchanged),
            removed=len(diff.removed),
            ingested_documents=ingested_documents,
            sync_run_id=sync_run_id,
        )
