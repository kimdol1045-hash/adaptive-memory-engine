from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from ame.bronze.schema import BronzeDocument


class BronzeStore:
    def __init__(self, corpus_root: Path):
        self.root = corpus_root / "bronze"
        self.documents = self.root / "documents"
        self.index = self.root / "index.jsonl"
        self.documents.mkdir(parents=True, exist_ok=True)

    def put(self, doc: BronzeDocument) -> BronzeDocument:
        existing = self._find_by_hash(doc.content_hash)
        if existing:
            return existing
        path = self.documents / f"{doc.id}.json"
        path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
        with self.index.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"id": doc.id, "content_hash": doc.content_hash, "source_id": doc.source_id}) + "\n")
        return doc

    def get(self, doc_id: str) -> BronzeDocument:
        return BronzeDocument.model_validate_json((self.documents / f"{doc_id}.json").read_text(encoding="utf-8"))

    def list(self) -> Iterable[BronzeDocument]:
        for path in sorted(self.documents.glob("*.json")):
            yield BronzeDocument.model_validate_json(path.read_text(encoding="utf-8"))

    def _find_by_hash(self, content_hash: str) -> BronzeDocument | None:
        for doc in self.list():
            if doc.content_hash == content_hash:
                return doc
        return None
