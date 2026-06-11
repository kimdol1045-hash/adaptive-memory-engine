from __future__ import annotations

from pydantic import BaseModel, Field


class GoldNode(BaseModel):
    id: str
    corpus_id: str
    type: str
    name: str
    canonical_name: str
    source_ids: list[str]


class GoldEdge(BaseModel):
    id: str
    corpus_id: str
    source: str
    relation: str
    target: str
    source_ids: list[str]
    weight: float = 1.0


class GoldTimelineEvent(BaseModel):
    id: str
    corpus_id: str
    event_type: str
    title: str
    status: str | None = None
    project: str | None = None
    rationale: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    supersedes: list[str] = Field(default_factory=list)
    superseded_by: list[str] = Field(default_factory=list)
    current: bool = False
    participants: list[str] = Field(default_factory=list)
    source_ids: list[str]
    confidence: float | None = None
