from __future__ import annotations

from ame.bronze.schema import BronzeDocument
from ame.gold.schema import GoldEdge, GoldNode


def to_custom_kg(nodes: list[GoldNode], edges: list[GoldEdge], chunks: list[BronzeDocument] | None = None) -> dict:
    return {
        "chunks": [
            {"content": chunk.content, "source_id": chunk.id}
            for chunk in chunks or []
        ],
        "entities": [
            {
                "entity_name": node.name,
                "entity_type": node.type,
                "description": node.name,
                "source_id": node.source_ids[0] if node.source_ids else "",
            }
            for node in nodes
        ],
        "relationships": [
            {
                "src_id": edge.source,
                "tgt_id": edge.target,
                "description": edge.relation,
                "keywords": edge.relation,
                "weight": edge.weight,
                "source_id": edge.source_ids[0] if edge.source_ids else "",
            }
            for edge in edges
        ],
    }
