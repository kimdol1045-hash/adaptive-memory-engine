from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ame.bronze.schema import BronzeDocument
from ame.connectors.base import SourceRef
from ame.connectors.json_helpers import as_list, first_present, read_json


class GitHubConnector:
    source_type = "github"

    def scan(self, path: Path) -> list[SourceRef]:
        root = path.expanduser().resolve()
        files = [root] if root.is_file() else sorted(root.rglob("*.json"))
        refs: list[SourceRef] = []
        for file in files:
            for row in as_list(read_json(file)):
                if not isinstance(row, dict):
                    continue
                number = str(first_present(row, "number", "id") or file.stem)
                kind = str(first_present(row, "kind", "type") or ("pull_request" if row.get("pull_request") else "issue"))
                refs.append(SourceRef(path=file, source_id=f"github:{kind}:{number}", content=self._item_content(row, kind, number)))
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
            metadata={"path": str(ref.path), "title": ref.source_id, "connector": "github"},
            content_hash=f"sha256:{digest}",
        )

    def _item_content(self, row: dict[str, Any], kind: str, number: str) -> str:
        title = str(first_present(row, "title", "summary", "name") or f"{kind} {number}")
        body = str(first_present(row, "body", "description", "content") or "")
        state = first_present(row, "state", "status")
        comments = first_present(row, "comments", "discussion") or []
        if isinstance(comments, dict):
            comments = as_list(comments)
        comment_text = "\n".join(f"- {first_present(comment, 'body', 'text', 'content')}" for comment in comments if isinstance(comment, dict))
        return "\n".join(
            [
                "---",
                f"title: {title}",
                f"github_kind: {kind}",
                f"github_number: {number}",
                f"state: {state or ''}",
                "---",
                "",
                f"# {title}",
                "",
                body,
                "",
                "## Comments",
                comment_text,
                "",
            ]
        )
