from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from ame.bronze.schema import BronzeDocument
from ame.connectors.base import SourceRef


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


class MarkdownConnector:
    source_type = "markdown"

    def scan(self, path: Path) -> list[SourceRef]:
        root = path.expanduser().resolve()
        files = [root] if root.is_file() else sorted([*root.rglob("*.md"), *root.rglob("*.markdown")])
        refs: list[SourceRef] = []
        for file in files:
            source_id = str(file.relative_to(root) if root.is_dir() else file.name)
            content = file.read_text(encoding="utf-8")
            sections = self._sections(content)
            if len(sections) <= 1:
                refs.append(SourceRef(path=file, source_id=source_id, content=content, root_source_id=source_id))
                continue
            for index, section in enumerate(sections):
                refs.append(
                    SourceRef(
                        path=file,
                        source_id=f"{source_id}#{self._safe_section_id(section['title'])}",
                        content=section["content"],
                        section_title=section["title"],
                        section_path=tuple(section["path"]),
                        section_level=section["level"],
                        section_index=index,
                        root_source_id=source_id,
                    )
                )
        return refs

    def load(self, corpus_id: str, ref: SourceRef) -> BronzeDocument:
        content = ref.content if ref.content is not None else ref.path.read_text(encoding="utf-8")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        metadata = self._metadata(content, ref.path)
        if ref.section_title:
            metadata["title"] = ref.section_title
            metadata["section_title"] = ref.section_title
            metadata["section_path"] = list(ref.section_path)
            metadata["section_level"] = ref.section_level
            metadata["section_index"] = ref.section_index
            metadata["root_source_id"] = ref.root_source_id or ref.source_id.split("#", 1)[0]
            metadata["source_file"] = ref.root_source_id or ref.source_id.split("#", 1)[0]
        return BronzeDocument(
            id=f"bronze_{digest[:16]}",
            corpus_id=corpus_id,
            source_type=self.source_type,
            source_id=ref.source_id,
            content=content,
            metadata=metadata,
            content_hash=f"sha256:{digest}",
        )

    def _metadata(self, content: str, path: Path) -> dict[str, Any]:
        metadata: dict[str, Any] = {"path": str(path), "title": path.stem}
        frontmatter = FRONTMATTER_RE.search(content)
        if frontmatter:
            metadata["frontmatter"] = self._parse_frontmatter(frontmatter.group(1))
            if title := metadata["frontmatter"].get("title"):
                metadata["title"] = title
        metadata["headings"] = [match.group(2).strip() for match in HEADING_RE.finditer(content)]
        if metadata["title"] == path.stem and metadata["headings"]:
            metadata["title"] = metadata["headings"][0]
        return metadata

    def _parse_frontmatter(self, text: str) -> dict[str, str]:
        data: dict[str, str] = {}
        for line in text.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"')
        return data

    def _sections(self, content: str) -> list[dict]:
        matches = [match for match in HEADING_RE.finditer(content) if len(match.group(1)) <= 2]
        if len(matches) <= 1:
            return []
        sections: list[dict] = []
        path_by_level: dict[int, str] = {}
        for index, match in enumerate(matches):
            level = len(match.group(1))
            title = match.group(2).strip()
            path_by_level[level] = title
            for deeper in [known for known in path_by_level if known > level]:
                del path_by_level[deeper]
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
            section_content = content[start:end].strip()
            if not section_content:
                continue
            sections.append(
                {
                    "title": title,
                    "level": level,
                    "path": [path_by_level[key] for key in sorted(path_by_level)],
                    "content": section_content,
                }
            )
        return sections

    def _safe_section_id(self, title: str) -> str:
        return re.sub(r"\s+", " ", title).strip().replace("/", "-").replace(":", " -")
