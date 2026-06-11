from pathlib import Path

from ame.connectors.obsidian import ObsidianConnector


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
