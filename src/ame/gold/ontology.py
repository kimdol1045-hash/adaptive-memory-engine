from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ENTITY_TYPES = [
    "Project",
    "Tool",
    "Concept",
    "Document",
    "Decision",
    "Meeting",
    "Email",
    "Issue",
    "Action",
    "Task",
    "Person",
    "Rationale",
]


DEFAULT_RELATION_RULES: dict[str, tuple[set[str], set[str]]] = {
    "USES": ({"Project", "Decision", "Tool", "Concept"}, {"Tool", "Project", "Concept"}),
    "ADOPTS": ({"Project", "Decision", "Concept"}, {"Tool", "Project", "Concept"}),
    "SELECTS": ({"Project", "Decision", "Concept"}, {"Tool", "Project", "Concept"}),
    "HAS_LAYER": ({"Project", "Concept"}, {"Concept"}),
    "STORES": ({"Concept"}, {"Concept"}),
    "EXTRACTS": ({"Concept"}, {"Concept"}),
    "PRODUCES": ({"Concept"}, {"Concept"}),
    "EXPORTS": ({"Concept"}, {"Concept"}),
    "EXPORTS_TO": ({"Concept"}, {"Tool", "Concept"}),
    "CONNECTS_TO": ({"Tool", "Concept"}, {"Concept"}),
    "VALIDATES": ({"Concept"}, {"Concept"}),
    "SELECTS_MODEL_BY": ({"Concept"}, {"Concept"}),
    "STATUS": ({"Decision", "Concept"}, {"Concept"}),
    "ROLE": ({"Tool", "Concept"}, {"Concept"}),
    "REQUIRES": ({"Project", "Concept"}, {"Concept"}),
    "CALLS": ({"Project", "Concept"}, {"Concept"}),
    "HAS_RATIONALE": ({"Decision", "Concept"}, {"Rationale"}),
    "SUPPORTED_BY": ({"Rationale"}, {"Document", "Concept"}),
    "CAUSED_BY": ({"Rationale"}, {"Concept"}),
    "ADDRESSES": ({"Rationale"}, {"Issue", "Concept"}),
    "MADE_IN": ({"Decision"}, {"Project"}),
    "RELATED_TO": (
        {"Project", "Tool", "Concept", "Document", "Meeting", "Email", "Issue", "Action", "Task", "Rationale"},
        {"Project", "Tool", "Concept", "Document", "Meeting", "Email", "Issue", "Action", "Task", "Rationale"},
    ),
    "SUPERSEDES": ({"Decision", "Concept"}, {"Decision", "Concept"}),
    "MENTIONS": ({"Document", "Meeting", "Email"}, {"Person", "Project", "Tool", "Concept", "Decision", "Issue", "Action", "Task"}),
}


def relation_type_valid(predicate: str, subject_types: set[str], object_types: set[str]) -> bool:
    rule = DEFAULT_RELATION_RULES.get(predicate)
    if not rule:
        return False
    domains, ranges = rule
    return bool(subject_types & domains) and bool(object_types & ranges)


def base_ontology_payload() -> dict[str, Any]:
    return {
        "version": 1,
        "entity_types": ENTITY_TYPES,
        "relation_rules": {
            relation: {"domain": sorted(domain), "range": sorted(range_)}
            for relation, (domain, range_) in DEFAULT_RELATION_RULES.items()
        },
    }


def write_base_ontology(path: Path, replace: bool = False) -> Path:
    if path.exists() and not replace:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(base_ontology_payload(), sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path
