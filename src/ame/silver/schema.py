from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SilverEntity(BaseModel):
    id: str
    corpus_id: str
    type: str
    name: str
    span: str | None = None
    aliases: list[str] = Field(default_factory=list)
    source_ids: list[str]
    confidence: float = 1.0


class SilverRelation(BaseModel):
    id: str
    corpus_id: str
    subject: str
    predicate: str
    object: str
    source_ids: list[str]
    confidence: float


class SilverDecision(BaseModel):
    id: str
    corpus_id: str
    title: str
    status: Literal["proposed", "accepted", "rejected", "superseded"]
    project: str | None = None
    rationale: str | None = None
    decision_date: str | None = None
    supersedes: list[str] = Field(default_factory=list)
    participants: list[str] = Field(default_factory=list)
    source_ids: list[str]
    confidence: float


class SilverRationale(BaseModel):
    id: str
    corpus_id: str
    decision_title: str
    rationale_text: str
    category: str
    span: str | None = None
    source_ids: list[str]
    confidence: float = 1.0
