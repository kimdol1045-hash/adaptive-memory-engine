from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in [
            "messages",
            "issues",
            "pull_requests",
            "prs",
            "discussions",
            "comments",
            "files",
            "documents",
            "threads",
            "events",
            "rows",
            "values",
            "items",
        ]:
            rows = value.get(key)
            if isinstance(rows, list):
                return rows
        return [value]
    return []


def first_present(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return None
