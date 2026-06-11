from __future__ import annotations

import re

from ame.connectors.markdown import MarkdownConnector


WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
TAG_RE = re.compile(r"(?<!\w)#([A-Za-z0-9_/-]+)")


class ObsidianConnector(MarkdownConnector):
    source_type = "obsidian"

    def _metadata(self, content: str, path):
        metadata = super()._metadata(content, path)
        metadata["wikilinks"] = sorted({m.group(1).split("|", 1)[0].strip() for m in WIKILINK_RE.finditer(content)})
        metadata["tags"] = sorted({m.group(1) for m in TAG_RE.finditer(content)})
        return metadata
