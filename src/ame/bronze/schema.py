from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class BronzeDocument(BaseModel):
    id: str
    corpus_id: str
    source_type: str
    source_id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
