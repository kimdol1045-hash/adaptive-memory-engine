from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QuerySource(BaseModel):
    source_id: str
    document: str
    source_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueryResult(BaseModel):
    answer: str
    sources: list[QuerySource] = Field(default_factory=list)
    confidence: float | None = None
    matches: list[str]
    raw: dict | None = None
