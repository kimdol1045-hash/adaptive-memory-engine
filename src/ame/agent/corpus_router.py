from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ame.agent.load_plan import LoadPlan, build_load_plan
from ame.core.paths import ensure_runtime_layout
from ame.core.state import CorpusStateStore


class CorpusSuggestion(BaseModel):
    source_path: str
    selected_corpus_id: str
    action: str
    confidence: float
    reason: str
    candidates: list[dict[str, Any]]
    load_plan: LoadPlan


def suggest_corpus(source_path: Path, profile: str | None = None) -> CorpusSuggestion:
    plan = build_load_plan(source_path, profile)
    path = source_path.expanduser().resolve()
    candidates = _rank_existing(path, plan)
    if candidates and candidates[0]["confidence"] >= 0.72:
        best = candidates[0]
        return CorpusSuggestion(
            source_path=str(path),
            selected_corpus_id=str(best["corpus_id"]),
            action="update_existing",
            confidence=float(best["confidence"]),
            reason=str(best["reason"]),
            candidates=candidates[:5],
            load_plan=plan,
        )
    corpus_id = _available_corpus_id(_slug(path.stem if path.is_file() else path.name))
    return CorpusSuggestion(
        source_path=str(path),
        selected_corpus_id=corpus_id,
        action="create_new",
        confidence=0.64,
        reason="No existing corpus matched this source strongly enough.",
        candidates=candidates[:5],
        load_plan=plan,
    )


def _rank_existing(path: Path, plan: LoadPlan) -> list[dict[str, Any]]:
    home = ensure_runtime_layout()
    corpora_root = home / "corpora"
    if not corpora_root.exists():
        return []
    incoming_names = {_root_source_id(row["source_id"]) for row in plan.largest_chunks}
    incoming_names.add(path.name)
    rows = []
    for child in sorted(corpora_root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        state = CorpusStateStore(child, corpus_id=child.name).read()
        score = 0.0
        reasons: list[str] = []
        if state.last_source_path:
            last = Path(state.last_source_path).expanduser()
            try:
                last_resolved = last.resolve()
            except OSError:
                last_resolved = last
            if last_resolved == path:
                score += 0.98
                reasons.append("same source_path")
            elif _contains(last_resolved, path) or _contains(path, last_resolved):
                score += 0.82
                reasons.append("source_path is in the same tree")
        existing_roots = {_root_source_id(document.source_id) for document in state.documents}
        overlap = len(existing_roots & incoming_names)
        if overlap:
            score += min(0.9, 0.35 + overlap * 0.08)
            reasons.append(f"{overlap} source_id root overlap(s)")
        path_tokens = set(_tokens(path.stem + " " + path.name))
        corpus_tokens = set(_tokens(child.name))
        token_overlap = path_tokens & corpus_tokens
        if token_overlap:
            score += min(0.3, len(token_overlap) * 0.1)
            reasons.append("name token overlap")
        if score > 0:
            rows.append(
                {
                    "corpus_id": child.name,
                    "confidence": round(min(score, 0.99), 2),
                    "reason": ", ".join(reasons),
                    "last_source_path": state.last_source_path,
                    "documents": len(state.documents),
                }
            )
    return sorted(rows, key=lambda row: float(row["confidence"]), reverse=True)


def _contains(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _root_source_id(source_id: str) -> str:
    return source_id.split("#", 1)[0].split("::chunk-", 1)[0]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-_")
    return slug or "documents"


def _available_corpus_id(base: str) -> str:
    corpora_root = ensure_runtime_layout() / "corpora"
    candidate = base
    index = 2
    while (corpora_root / candidate).exists():
        candidate = f"{base}-{index}"
        index += 1
    return candidate


def _tokens(value: str) -> list[str]:
    return [token for token in re.split(r"[^a-zA-Z0-9]+", value.lower()) if token]
