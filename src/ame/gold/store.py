from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from ame.gold.schema import GoldEdge, GoldNode, GoldTimelineEvent

T = TypeVar("T", bound=BaseModel)


class GoldStore:
    def __init__(self, corpus_root: Path):
        self.root = corpus_root / "gold"
        self.root.mkdir(parents=True, exist_ok=True)

    def replace(self, nodes: list[GoldNode], edges: list[GoldEdge], timeline: list[GoldTimelineEvent] | None = None) -> None:
        self._write("nodes.jsonl", nodes)
        self._write("edges.jsonl", edges)
        self._write("timeline.jsonl", timeline or [])
        self._write("supersedes.jsonl", [edge for edge in edges if edge.relation == "SUPERSEDES"])

    def nodes(self) -> list[GoldNode]:
        return self._read("nodes.jsonl", GoldNode)

    def edges(self) -> list[GoldEdge]:
        return self._read("edges.jsonl", GoldEdge)

    def supersedes(self) -> list[GoldEdge]:
        return self._read("supersedes.jsonl", GoldEdge)

    def timeline(self) -> list[GoldTimelineEvent]:
        return self._read("timeline.jsonl", GoldTimelineEvent)

    def _write(self, name: str, rows: list[BaseModel]) -> None:
        with (self.root / name).open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(row.model_dump_json() + "\n")

    def _read(self, name: str, model: type[T]) -> list[T]:
        path = self.root / name
        if not path.exists():
            return []
        return [model.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
