from __future__ import annotations

import hashlib
import re
from typing import Any

from pydantic import BaseModel, Field


class ContextItem(BaseModel):
    source_id: str
    content: str
    priority: float = 0.5
    metadata: dict[str, Any] = Field(default_factory=dict)


class OptimizedContextItem(BaseModel):
    source_id: str
    content: str
    original_hash: str
    compression: str = "none"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextBudgetResult(BaseModel):
    budget_chars: int
    original_chars: int
    optimized_chars: int
    items: list[OptimizedContextItem] = Field(default_factory=list)
    archive: dict[str, str] = Field(default_factory=dict)


class ContextBudgetOptimizer:
    def optimize(self, items: list[ContextItem], budget_chars: int) -> ContextBudgetResult:
        if budget_chars < 1:
            raise ValueError("budget_chars must be at least 1")
        ordered = sorted(enumerate(items), key=lambda pair: (-pair[1].priority, pair[0]))
        original_chars = sum(len(item.content) for item in items)
        optimized: list[OptimizedContextItem] = []
        archive: dict[str, str] = {}
        remaining = budget_chars

        for _index, item in ordered:
            original_hash = _hash(item.content)
            if remaining <= 0 and optimized:
                archive[original_hash] = item.content
                continue
            if len(item.content) <= remaining:
                content = item.content
                compression = "none"
            else:
                content = _compress(item.content, max(1, remaining))
                compression = "extractive"
                archive[original_hash] = item.content
            optimized.append(
                OptimizedContextItem(
                    source_id=item.source_id,
                    content=content,
                    original_hash=original_hash,
                    compression=compression,
                    metadata=item.metadata,
                )
            )
            remaining = max(0, remaining - len(content))

        optimized_chars = sum(len(item.content) for item in optimized)
        return ContextBudgetResult(
            budget_chars=budget_chars,
            original_chars=original_chars,
            optimized_chars=optimized_chars,
            items=optimized,
            archive=archive,
        )

    def restore(self, result: ContextBudgetResult) -> list[ContextItem]:
        restored: list[ContextItem] = []
        for item in result.items:
            restored.append(
                ContextItem(
                    source_id=item.source_id,
                    content=result.archive.get(item.original_hash, item.content),
                    metadata=item.metadata,
                )
            )
        return restored


def _compress(content: str, limit: int) -> str:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    key_lines = [
        line
        for line in lines
        if re.search(r"\b(decision|rationale|because|next action|todo|blocker|결정|근거|이유|할 일|차단)\b", line, re.I)
    ]
    selected = []
    for line in lines[:2] + key_lines:
        if line not in selected:
            selected.append(line)
    text = "\n".join(selected) if selected else content.strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
