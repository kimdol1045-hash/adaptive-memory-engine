from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field


class IngestedDocumentState(BaseModel):
    id: str
    source_id: str
    content_hash: str


class CorpusState(BaseModel):
    corpus_id: str
    last_ingest_at: datetime | None = None
    last_source_path: str | None = None
    last_mode: str | None = None
    documents: list[IngestedDocumentState] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)


class CorpusStateStore:
    def __init__(self, corpus_root: Path):
        self.path = corpus_root / "state.db"
        self.legacy_path = corpus_root / "state.json"
        self.corpus_id = corpus_root.name

    def read(self) -> CorpusState:
        path = self.path if self.path.exists() and self.path.read_text(encoding="utf-8").strip() else self.legacy_path
        if not path.exists():
            return CorpusState(corpus_id=self.corpus_id)
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return CorpusState(corpus_id=self.corpus_id)
        return CorpusState.model_validate_json(text)

    def record_ingest(
        self,
        source_path: Path,
        mode: str,
        documents: list[IngestedDocumentState],
        counts: dict[str, int],
    ) -> CorpusState:
        state = CorpusState(
            corpus_id=self.corpus_id,
            last_ingest_at=datetime.now(timezone.utc),
            last_source_path=str(source_path),
            last_mode=mode,
            documents=documents,
            counts=counts,
        )
        payload = state.model_dump_json(indent=2)
        self.path.write_text(payload, encoding="utf-8")
        self.legacy_path.write_text(payload, encoding="utf-8")
        return state
