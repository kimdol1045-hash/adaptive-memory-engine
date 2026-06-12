from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime, timezone
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

    def remove(self, doc_ids: Iterable[str]) -> None:
        targets = set(doc_ids)
        if not targets:
            return
        for doc_id in targets:
            path = self.documents / f"{doc_id}.json"
            if path.exists():
                path.unlink()
        self._rebuild_index()

    def mark_active(self, doc_ids: Iterable[str]) -> None:
        self._set_active(doc_ids, active=True)

    def mark_inactive(self, doc_ids: Iterable[str]) -> None:
        self._set_active(doc_ids, active=False)

    def _find_by_hash(self, content_hash: str) -> BronzeDocument | None:
        for doc in self.list():
            if doc.content_hash == content_hash:
                return doc
        return None

    def _rebuild_index(self) -> None:
        rows = [
            {"id": doc.id, "content_hash": doc.content_hash, "source_id": doc.source_id}
            for doc in self.list()
        ]
        self.index.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )

    def _set_active(self, doc_ids: Iterable[str], *, active: bool) -> None:
        now = datetime.now(timezone.utc).isoformat()
        for doc_id in set(doc_ids):
            path = self.documents / f"{doc_id}.json"
            if not path.exists():
                continue
            doc = BronzeDocument.model_validate_json(path.read_text(encoding="utf-8"))
            metadata = dict(doc.metadata)
            metadata["active"] = active
            if active:
                metadata.pop("superseded_at", None)
            else:
                metadata["superseded_at"] = now
            updated = doc.model_copy(update={"metadata": metadata})
            path.write_text(updated.model_dump_json(indent=2), encoding="utf-8")
