from pathlib import Path

from ame.connectors.obsidian import ObsidianConnector
from ame.connectors.markdown import DEFAULT_MAX_CHUNK_CHARS, MarkdownConnector


def test_obsidian_connector_extracts_metadata(tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    note.write_text("---\nproject: OpenClaw\n---\n# Title\n[[LightRAG]] #memory\n", encoding="utf-8")

    connector = ObsidianConnector()
    refs = connector.scan(tmp_path)
    doc = connector.load("openclaw", refs[0])

    assert doc.metadata["frontmatter"]["project"] == "OpenClaw"
    assert doc.metadata["title"] == "Title"
    assert doc.metadata["wikilinks"] == ["LightRAG"]
    assert doc.metadata["tags"] == ["memory"]


def test_markdown_connector_splits_large_sections_under_embedding_context(tmp_path: Path) -> None:
    note = tmp_path / "large.md"
    note.write_text("# Large\n" + ("large paragraph " * 260), encoding="utf-8")

    refs = MarkdownConnector().scan(note)

    assert len(refs) > 1
    assert max(len(ref.content or "") for ref in refs) <= DEFAULT_MAX_CHUNK_CHARS
    assert refs[0].metadata["chunk_total"] == len(refs)
