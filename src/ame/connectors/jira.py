from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ame.bronze.schema import BronzeDocument
from ame.connectors.base import SourceRef
from ame.connectors.json_helpers import as_list, first_present, read_json


class JiraConnector:
    source_type = "jira"

    def scan(self, path: Path) -> list[SourceRef]:
        root = path.expanduser().resolve()
        files = [root] if root.is_file() else sorted(root.rglob("*.json"))
        refs: list[SourceRef] = []
        for file in files:
            for row in as_list(read_json(file)):
                if not isinstance(row, dict):
                    continue
                key = str(first_present(row, "key", "id", "issue_key") or file.stem)
                refs.append(SourceRef(path=file, source_id=f"jira:{key}", content=self._issue_content(row, key)))
        return refs

    def load(self, corpus_id: str, ref: SourceRef) -> BronzeDocument:
        content = ref.content or ref.path.read_text(encoding="utf-8")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        key = ref.source_id.split(":", 1)[-1]
        return BronzeDocument(
            id=f"bronze_{digest[:16]}",
            corpus_id=corpus_id,
            source_type=self.source_type,
            source_id=ref.source_id,
            content=content,
            metadata={"path": str(ref.path), "issue_key": key, "title": f"Jira {key}", "connector": "jira"},
            content_hash=f"sha256:{digest}",
        )

    def _issue_content(self, row: dict[str, Any], key: str) -> str:
        fields = row.get("fields") if isinstance(row.get("fields"), dict) else row
        summary = str(first_present(fields, "summary", "title", "name") or key)
        description = str(first_present(fields, "description", "body", "content") or "")
        status = first_present(fields, "status", "state")
        comments = first_present(fields, "comments", "comment") or []
        if isinstance(comments, dict):
            comments = comments.get("comments", [])
        comment_text = "\n".join(f"- {first_present(comment, 'body', 'text', 'content')}" for comment in comments if isinstance(comment, dict))
        return "\n".join(
            [
                "---",
                f"title: {summary}",
                f"issue_key: {key}",
                f"status: {status or ''}",
                "---",
                "",
                f"# {summary}",
                "",
                description,
                "",
                "## Comments",
                comment_text,
                "",
            ]
        )
