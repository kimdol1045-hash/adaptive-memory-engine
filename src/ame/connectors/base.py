from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ame.bronze.schema import BronzeDocument


@dataclass(frozen=True)
class SourceRef:
    path: Path
    source_id: str
    content: str | None = None
    section_title: str | None = None
    section_path: tuple[str, ...] = ()
    section_level: int | None = None
    section_index: int | None = None
    root_source_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Connector(Protocol):
    source_type: str

    def scan(self, path: Path) -> list[SourceRef]:
        ...

    def load(self, corpus_id: str, ref: SourceRef) -> BronzeDocument:
        ...
