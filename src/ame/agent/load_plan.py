from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ame.connectors.base import SourceRef
from ame.connectors.router import ConnectorRouter


class LoadPlan(BaseModel):
    source_path: str
    connector: str
    source_files: int
    bronze_chunks: int
    total_chars: int
    total_lines: int
    largest_chunk_chars: int
    largest_chunks: list[dict[str, Any]]
    estimated_llm_calls: int
    estimated_minutes: dict[str, int]
    risk: str
    recommendation: str
    warnings: list[str]


def build_load_plan(source_path: Path, profile: str | None = None) -> LoadPlan:
    path = source_path.expanduser().resolve()
    connector = ConnectorRouter().resolve(path, profile)
    refs = connector.scan(path)
    contents = [_content_for_ref(ref) for ref in refs]
    total_chars = sum(len(content) for content in contents)
    total_lines = sum(content.count("\n") + (1 if content else 0) for content in contents)
    source_files = len({_root_source(ref) for ref in refs})
    largest = sorted(
        [
            {
                "source_id": ref.source_id,
                "path": str(ref.path),
                "chars": len(content),
                "lines": content.count("\n") + (1 if content else 0),
            }
            for ref, content in zip(refs, contents, strict=True)
        ],
        key=lambda row: int(row["chars"]),
        reverse=True,
    )[:5]
    estimated_calls = len(refs)
    risk = _risk(total_chars=total_chars, chunks=estimated_calls, largest_chunk_chars=int(largest[0]["chars"]) if largest else 0)
    warnings = _warnings(refs, contents, risk)
    return LoadPlan(
        source_path=str(path),
        connector=connector.source_type,
        source_files=source_files,
        bronze_chunks=len(refs),
        total_chars=total_chars,
        total_lines=total_lines,
        largest_chunk_chars=int(largest[0]["chars"]) if largest else 0,
        largest_chunks=largest,
        estimated_llm_calls=estimated_calls,
        estimated_minutes=_estimated_minutes(estimated_calls),
        risk=risk,
        recommendation=_recommendation(risk, estimated_calls),
        warnings=warnings,
    )


def _content_for_ref(ref: SourceRef) -> str:
    if ref.content is not None:
        return ref.content
    try:
        return ref.path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ref.path.read_text(encoding="utf-8", errors="replace")


def _root_source(ref: SourceRef) -> str:
    return ref.root_source_id or ref.source_id.split("#", 1)[0]


def _risk(*, total_chars: int, chunks: int, largest_chunk_chars: int) -> str:
    if chunks == 0:
        return "blocked"
    if chunks >= 120 or total_chars >= 180_000 or largest_chunk_chars >= 2_400:
        return "high"
    if chunks >= 40 or total_chars >= 60_000 or largest_chunk_chars >= 1_800:
        return "medium"
    return "low"


def _estimated_minutes(calls: int) -> dict[str, int]:
    if calls <= 0:
        return {"min": 0, "max": 0}
    # T1 local LLM extraction varies heavily by model load and chunk shape.
    return {"min": max(1, calls // 6), "max": max(2, calls // 2)}


def _warnings(refs: list[SourceRef], contents: list[str], risk: str) -> list[str]:
    warnings: list[str] = []
    if not refs:
        warnings.append("No supported documents were found at source_path.")
    if risk == "high":
        warnings.append("This source is large for local LLM extraction. Start as a background job and expect a long run.")
    if any("```" in content for content in contents):
        warnings.append("Code fences were detected. Schema-like or code-heavy chunks may produce weaker extraction.")
    if any(len(content) >= 2_000 for content in contents):
        warnings.append("Some chunks are near or above the comfortable local extraction size.")
    return warnings


def _recommendation(risk: str, calls: int) -> str:
    if risk == "blocked":
        return "No supported documents found. Check the path or connector profile."
    if risk == "high":
        return "Use a new clean corpus and run ame_load in background. If it is too slow, split the document into smaller digest files."
    if risk == "medium":
        return "Use a new clean corpus and run ame_load in background. Poll ame_load_status until completed."
    if calls <= 5:
        return "Safe to run ame_load directly or in background."
    return "Safe to run ame_load in background."
