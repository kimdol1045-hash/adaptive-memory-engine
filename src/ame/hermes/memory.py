from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from ame.bronze.schema import BronzeDocument
from ame.core.corpus import require_corpus


PersonalMemoryType = Literal[
    "Project",
    "Idea",
    "Decision",
    "Task",
    "Person",
    "Meeting",
    "Document",
    "Email",
    "Action",
    "Preference",
    "Routine",
]


class PersonalMemory(BaseModel):
    id: str
    type: PersonalMemoryType
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)
    source: str = "hermes"
    source_id: str | None = None
    source_url: str | None = None
    metadata: dict[str, str | int | float | bool | list[str] | None] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HermesRecallResult(BaseModel):
    query: str
    memories: list[PersonalMemory] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reasoning_depth: int = 1


class HermesMemoryStore:
    def __init__(self, corpus_id: str):
        self.corpus_root = require_corpus(corpus_id)
        self.path = self.corpus_root / "personal" / "memories.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        memory_type: PersonalMemoryType,
        title: str,
        content: str,
        tags: list[str] | None = None,
        source: str = "hermes",
        source_id: str | None = None,
        source_url: str | None = None,
        metadata: dict[str, str | int | float | bool | list[str] | None] | None = None,
    ) -> PersonalMemory:
        memory = PersonalMemory(
            id=f"personal_{len(self.list()) + 1:06d}",
            type=memory_type,
            title=title,
            content=content,
            tags=tags or [],
            source=source,
            source_id=source_id,
            source_url=source_url,
            metadata=metadata or {},
        )
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(memory.model_dump_json() + "\n")
        return memory

    def write_from_bronze(self, doc: BronzeDocument) -> PersonalMemory:
        existing = next((memory for memory in self.list() if memory.source_id == doc.source_id), None)
        if existing:
            return existing
        memory_type = self._memory_type(doc)
        title = str(doc.metadata.get("title") or doc.source_id)
        tags = sorted({doc.source_type, str(doc.metadata.get("google_service") or ""), str(doc.metadata.get("connector") or "")} - {""})
        return self.write(
            memory_type,
            title,
            doc.content,
            tags=tags,
            source=str(doc.metadata.get("connector") or doc.source_type),
            source_id=doc.source_id,
            source_url=_optional_text(doc.metadata.get("original_url")),
            metadata=_personal_metadata(doc.metadata),
        )

    def import_bronze(self, docs: list[BronzeDocument]) -> list[PersonalMemory]:
        return [self.write_from_bronze(doc) for doc in docs]

    def list(self) -> list[PersonalMemory]:
        if not self.path.exists():
            return []
        return [PersonalMemory.model_validate_json(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def recall(self, query: str) -> HermesRecallResult:
        normalized = query.casefold()
        memories = [
            memory
            for memory in self.list()
            if normalized in memory.title.casefold()
            or normalized in memory.content.casefold()
            or any(normalized in tag.casefold() for tag in memory.tags)
            or normalized in memory.type.casefold()
        ]
        return self._result(query, memories)

    def recall_project(self, project: str) -> HermesRecallResult:
        return self.recall(project)

    def recall_person(self, person: str) -> HermesRecallResult:
        return self.recall(person)

    def recall_decisions(self, topic: str) -> HermesRecallResult:
        result = self.recall(topic)
        result.memories = [memory for memory in result.memories if memory.type == "Decision"]
        result.sources = self._sources(result.memories)
        result.confidence = self._confidence(result.memories)
        return result

    def recall_next_actions(self) -> HermesRecallResult:
        memories = [
            memory
            for memory in self.list()
            if memory.type in {"Task", "Action"} or "next" in memory.content.casefold() or "priority" in memory.content.casefold()
        ]
        return self._result("next_actions", memories)

    def recall_timeline(self, date_from: str | None = None, date_to: str | None = None) -> HermesRecallResult:
        memories = []
        for memory in self.list():
            occurred = _memory_time(memory)
            if date_from and occurred and occurred < date_from:
                continue
            if date_to and occurred and occurred > date_to:
                continue
            memories.append(memory)
        memories.sort(key=lambda memory: _memory_time(memory) or memory.created_at.isoformat(), reverse=True)
        query = f"timeline:{date_from or '*'}..{date_to or '*'}"
        return self._result(query, memories)

    def _result(self, query: str, memories: list[PersonalMemory]) -> HermesRecallResult:
        return HermesRecallResult(
            query=query,
            memories=memories,
            sources=self._sources(memories),
            confidence=self._confidence(memories),
            reasoning_depth=max(1, min(4, len({memory.type for memory in memories}) or 1)),
        )

    def _sources(self, memories: list[PersonalMemory]) -> list[str]:
        return [memory.source_id or memory.source for memory in memories if memory.source_id or memory.source]

    def _confidence(self, memories: list[PersonalMemory]) -> float:
        if not memories:
            return 0.0
        return min(0.95, 0.62 + min(len(memories), 5) * 0.06)

    def _memory_type(self, doc: BronzeDocument) -> PersonalMemoryType:
        requested = doc.metadata.get("memory_type")
        allowed = set(PersonalMemoryType.__args__)  # type: ignore[attr-defined]
        if isinstance(requested, str) and requested in allowed:
            return requested  # type: ignore[return-value]
        source_map: dict[str, PersonalMemoryType] = {
            "google_drive": "Document",
            "gmail": "Email",
            "google_calendar": "Meeting",
            "google_sheets": "Document",
            "jira": "Task",
            "github": "Document",
            "slack": "Decision",
        }
        return source_map.get(doc.source_type, "Document")


def _personal_metadata(metadata: dict) -> dict[str, str | int | float | bool | list[str] | None]:
    allowed: dict[str, str | int | float | bool | list[str] | None] = {}
    for key, value in metadata.items():
        if isinstance(value, str | int | float | bool) or value is None:
            allowed[key] = value
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            allowed[key] = value
    return allowed


def _optional_text(value) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _memory_time(memory: PersonalMemory) -> str | None:
    for key in ["occurred_at", "start", "date", "modified_at", "created_at"]:
        value = memory.metadata.get(key)
        if value:
            return str(value)
    return memory.created_at.isoformat()
