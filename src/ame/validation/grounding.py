from __future__ import annotations

from ame.bronze.schema import BronzeDocument
from ame.silver.schema import SilverEntity


def is_grounded(entity: SilverEntity, docs: dict[str, BronzeDocument]) -> bool:
    if entity.span is None:
        return True
    return any(entity.span in docs[source_id].content for source_id in entity.source_ids if source_id in docs)
