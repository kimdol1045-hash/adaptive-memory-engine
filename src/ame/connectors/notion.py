from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ame.bronze.schema import BronzeDocument
from ame.connectors.base import SourceRef
from ame.connectors.json_helpers import as_list, first_present, read_json


class NotionConnector:
    source_type = "notion"

    def scan(self, path: Path) -> list[SourceRef]:
        root = path.expanduser().resolve()
        files = [root] if root.is_file() else sorted(root.rglob("*.json"))
        refs: list[SourceRef] = []
        for file in files:
            for row in as_list(read_json(file)):
                if not isinstance(row, dict):
                    continue
                page_id = str(first_present(row, "id", "page_id") or file.stem)
                refs.append(SourceRef(path=file, source_id=f"notion:{page_id}", content=self._page_content(row, page_id)))
        return refs

    def load(self, corpus_id: str, ref: SourceRef) -> BronzeDocument:
        content = ref.content or ref.path.read_text(encoding="utf-8")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return BronzeDocument(
            id=f"bronze_{digest[:16]}",
            corpus_id=corpus_id,
            source_type=self.source_type,
            source_id=ref.source_id,
            content=content,
            metadata={"path": str(ref.path), "title": ref.source_id, "connector": "notion"},
            content_hash=f"sha256:{digest}",
        )

    def _page_content(self, row: dict[str, Any], page_id: str) -> str:
        title = str(first_present(row, "title", "name") or page_id)
        body = str(first_present(row, "content", "body", "text") or "")
        url = str(first_present(row, "url", "public_url") or "")
        last_edited_time = str(first_present(row, "last_edited_time", "updated_at") or "")
        return "\n".join(
            [
                "---",
                f"title: {title}",
                f"notion_page_id: {page_id}",
                f"url: {url}",
                f"last_edited_time: {last_edited_time}",
                "---",
                "",
                f"# {title}",
                "",
                body,
                "",
            ]
        )
