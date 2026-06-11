from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ame.bronze.schema import BronzeDocument
from ame.connectors.base import SourceRef
from ame.connectors.json_helpers import as_list, first_present, read_json


class SlackExportConnector:
    source_type = "slack"

    def scan(self, path: Path) -> list[SourceRef]:
        root = path.expanduser().resolve()
        files = [root] if root.is_file() else sorted(root.rglob("*.json"))
        refs: list[SourceRef] = []
        for file in files:
            rows = as_list(read_json(file))
            channel = file.parent.name if file.parent != root else file.stem
            for index, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                ts = str(first_present(row, "ts", "timestamp", "created_at") or index)
                source_id = f"slack:{channel}:{ts}"
                refs.append(SourceRef(path=file, source_id=source_id, content=self._message_content(channel, row, ts)))
        return refs

    def load(self, corpus_id: str, ref: SourceRef) -> BronzeDocument:
        content = ref.content or ref.path.read_text(encoding="utf-8")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        parts = ref.source_id.split(":")
        channel = parts[1] if len(parts) > 1 else ref.path.parent.name
        return BronzeDocument(
            id=f"bronze_{digest[:16]}",
            corpus_id=corpus_id,
            source_type=self.source_type,
            source_id=ref.source_id,
            content=content,
            metadata={"path": str(ref.path), "channel": channel, "title": f"Slack #{channel}", "connector": "slack-export"},
            content_hash=f"sha256:{digest}",
        )

    def _message_content(self, channel: str, row: dict[str, Any], ts: str) -> str:
        user = first_present(row, "user", "username", "author") or "unknown"
        text = str(first_present(row, "text", "message", "content") or "")
        thread_ts = first_present(row, "thread_ts", "parent_ts")
        return "\n".join(
            [
                "---",
                f"title: Slack #{channel} {ts}",
                f"channel: {channel}",
                f"user: {user}",
                f"timestamp: {ts}",
                "---",
                "",
                f"# Slack #{channel}",
                "",
                f"User: {user}",
                "",
                text,
                f"Thread: {thread_ts}" if thread_ts else "",
                "",
            ]
        )
