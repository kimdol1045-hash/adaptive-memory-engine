from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from ame.silver.schema import SilverDecision, SilverEntity, SilverRationale, SilverRelation

T = TypeVar("T", bound=BaseModel)


class SilverStore:
    def __init__(self, corpus_root: Path):
        self.root = corpus_root / "silver"
        self.root.mkdir(parents=True, exist_ok=True)

    def replace(
        self,
        entities: list[SilverEntity],
        relations: list[SilverRelation],
        decisions: list[SilverDecision],
        rejected: list[dict],
        rationales: list[SilverRationale] | None = None,
    ) -> None:
        self._write("entities.jsonl", entities)
        self._write("relations.jsonl", relations)
        self._write("decisions.jsonl", decisions)
        self._write("rationales.jsonl", rationales or [])
        self._write_dicts("rejected.jsonl", rejected)

    def entities(self) -> list[SilverEntity]:
        return self._read("entities.jsonl", SilverEntity)

    def relations(self) -> list[SilverRelation]:
        return self._read("relations.jsonl", SilverRelation)

    def decisions(self) -> list[SilverDecision]:
        return self._read("decisions.jsonl", SilverDecision)

    def rationales(self) -> list[SilverRationale]:
        return self._read("rationales.jsonl", SilverRationale)

    def _write(self, name: str, rows: list[BaseModel]) -> None:
        with (self.root / name).open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(row.model_dump_json() + "\n")

    def _write_dicts(self, name: str, rows: list[dict]) -> None:
        with (self.root / name).open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _read(self, name: str, model: type[T]) -> list[T]:
        path = self.root / name
        if not path.exists():
            return []
        return [model.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
