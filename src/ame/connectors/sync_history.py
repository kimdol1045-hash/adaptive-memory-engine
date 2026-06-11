from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class ConnectorSyncRun(BaseModel):
    id: str = Field(default_factory=lambda: f"sync_{uuid.uuid4().hex[:12]}")
    corpus_id: str
    connector: str
    status: Literal["success", "failed"]
    source: str | None = None
    started_at: datetime
    finished_at: datetime
    counts: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class ConnectorSyncStore:
    def __init__(self, corpus_root: Path):
        self.corpus_root = corpus_root
        self.path = corpus_root / "connectors" / "sync_history.jsonl"

    def record(
        self,
        *,
        connector: str,
        status: Literal["success", "failed"],
        started_at: datetime,
        source: str | None = None,
        counts: dict[str, int] | None = None,
        metadata: dict[str, str] | None = None,
        error: str | None = None,
    ) -> ConnectorSyncRun:
        run = ConnectorSyncRun(
            corpus_id=self.corpus_root.name,
            connector=connector,
            status=status,
            source=source,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            counts=counts or {},
            metadata=metadata or {},
            error=error,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(run.model_dump_json() + "\n")
        return run

    def list(self, *, connector: str | None = None, limit: int | None = None) -> list[ConnectorSyncRun]:
        if not self.path.exists():
            return []
        rows: list[ConnectorSyncRun] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = ConnectorSyncRun.model_validate(json.loads(line))
            if connector and row.connector != connector:
                continue
            rows.append(row)
        rows.sort(key=lambda run: run.started_at, reverse=True)
        return rows[:limit] if limit else rows

    def latest(self, *, connector: str | None = None) -> ConnectorSyncRun | None:
        rows = self.list(connector=connector, limit=1)
        return rows[0] if rows else None
