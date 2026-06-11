from __future__ import annotations

from pathlib import Path

from ame.core.errors import CorpusNotFoundError
from ame.core.paths import corpus_path, ensure_corpus_layout


def create_corpus(corpus_id: str) -> Path:
    return ensure_corpus_layout(corpus_id)


def require_corpus(corpus_id: str) -> Path:
    root = corpus_path(corpus_id)
    if not root.exists():
        raise CorpusNotFoundError(f"Corpus does not exist: {corpus_id}")
    return root
