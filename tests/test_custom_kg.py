from ame.bronze.schema import BronzeDocument
from ame.gold.schema import GoldEdge, GoldNode
from ame.storage.custom_kg import to_custom_kg


def test_custom_kg_includes_chunks_entities_and_relationships() -> None:
    doc = BronzeDocument(
        id="bronze_1",
        corpus_id="openclaw",
        source_type="markdown",
        source_id="openclaw.md",
        content="OpenClaw uses LightRAG",
        content_hash="sha256:x",
    )
    node = GoldNode(id="node_1", corpus_id="openclaw", type="Tool", name="LightRAG", canonical_name="lightrag", source_ids=["bronze_1"])
    edge = GoldEdge(id="edge_1", corpus_id="openclaw", source="OpenClaw", relation="USES", target="LightRAG", source_ids=["bronze_1"])

    kg = to_custom_kg([node], [edge], [doc])

    assert kg["chunks"][0]["source_id"] == "bronze_1"
    assert kg["entities"][0]["description"] == "LightRAG"
    assert kg["relationships"][0]["keywords"] == "USES"
