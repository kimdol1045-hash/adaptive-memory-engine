from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RetrieveResult(BaseModel):
    query: str
    matches: list[dict[str, Any]] = Field(default_factory=list)


class GraphResult(BaseModel):
    entity: str
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


class DecisionsResult(BaseModel):
    project: str | None = None
    current_only: bool = True
    decisions: list[dict[str, Any]] = Field(default_factory=list)


class WriteResult(BaseModel):
    kind: str
    path: str
    title: str
    ingested: bool = True
    raw: dict[str, Any] = Field(default_factory=dict)
