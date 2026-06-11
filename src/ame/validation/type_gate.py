from __future__ import annotations

from ame.gold.ontology import DEFAULT_RELATION_RULES
from ame.silver.schema import SilverEntity, SilverRelation


RELATION_RULES = DEFAULT_RELATION_RULES


def relation_type_valid(relation: SilverRelation, entities: list[SilverEntity]) -> bool:
    rule = RELATION_RULES.get(relation.predicate)
    if not rule:
        return False
    by_name: dict[str, set[str]] = {}
    for entity in entities:
        by_name.setdefault(entity.name, set()).add(entity.type)
    subject_types = by_name.get(relation.subject)
    object_types = by_name.get(relation.object)
    if subject_types is None or object_types is None:
        return False
    domains, ranges = rule
    return bool(subject_types & domains) and bool(object_types & ranges)
