from ame.bronze.schema import BronzeDocument
from ame.silver.extractor import DeterministicExtractor


def test_extractor_does_not_turn_considered_tool_into_uses_relation() -> None:
    doc = BronzeDocument(
        id="bronze_1",
        corpus_id="openclaw",
        source_type="markdown",
        source_id="openclaw.md",
        content=(
            "---\nproject: OpenClaw\n---\n"
            "OpenClaw decided to use LightRAG as the storage core.\n"
            "The team considered building GraphRAG directly.\n"
        ),
        metadata={"frontmatter": {"project": "OpenClaw"}, "headings": [], "wikilinks": [], "tags": []},
        content_hash="sha256:x",
    )

    _, relations, _ = DeterministicExtractor().extract(doc)

    assert [(relation.predicate, relation.object) for relation in relations] == [("USES", "LightRAG")]


def test_extractor_creates_related_to_for_wikilinks() -> None:
    doc = BronzeDocument(
        id="bronze_1",
        corpus_id="openclaw",
        source_type="obsidian",
        source_id="openclaw.md",
        content="# OpenClaw\nRelated notes: [[Adaptive Memory Engine]]\n",
        metadata={
            "title": "OpenClaw",
            "frontmatter": {},
            "headings": ["OpenClaw"],
            "wikilinks": ["Adaptive Memory Engine"],
            "tags": [],
        },
        content_hash="sha256:x",
    )

    _, relations, _ = DeterministicExtractor().extract(doc)

    assert [(relation.subject, relation.predicate, relation.object) for relation in relations] == [
        ("OpenClaw", "RELATED_TO", "Adaptive Memory Engine")
    ]
