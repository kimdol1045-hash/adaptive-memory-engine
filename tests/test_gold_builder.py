from ame.gold.builder import GoldBuilder
from ame.silver.schema import SilverDecision, SilverEntity, SilverRelation


def test_gold_builder_promotes_decisions_to_nodes_timeline_and_edges() -> None:
    entities = [
        SilverEntity(
            id="entity_project",
            corpus_id="openclaw",
            type="Project",
            name="OpenClaw",
            span="OpenClaw",
            source_ids=["bronze_1"],
        ),
        SilverEntity(
            id="entity_tool",
            corpus_id="openclaw",
            type="Tool",
            name="LightRAG",
            span="LightRAG",
            source_ids=["bronze_1"],
        ),
    ]
    relations = [
        SilverRelation(
            id="relation_1",
            corpus_id="openclaw",
            subject="OpenClaw",
            predicate="USES",
            object="LightRAG",
            source_ids=["bronze_1"],
            confidence=0.9,
        )
    ]
    decisions = [
        SilverDecision(
            id="decision_1",
            corpus_id="openclaw",
            title="LightRAG adoption",
            status="accepted",
            project="OpenClaw",
            rationale="Use LightRAG as the storage core.",
            supersedes=["GraphRAG adoption"],
            source_ids=["bronze_1"],
            confidence=0.8,
        )
    ]

    nodes, edges, timeline = GoldBuilder().build(entities, relations, decisions)

    assert {(node.type, node.name) for node in nodes} == {
        ("Project", "OpenClaw"),
        ("Tool", "LightRAG"),
        ("Decision", "LightRAG adoption"),
    }
    assert {(edge.source, edge.relation, edge.target) for edge in edges} == {
        ("OpenClaw", "USES", "LightRAG"),
        ("LightRAG adoption", "MADE_IN", "OpenClaw"),
        ("LightRAG adoption", "SUPERSEDES", "GraphRAG adoption"),
        ("LightRAG adoption", "USES", "LightRAG"),
    }
    assert timeline[0].title == "LightRAG adoption"
    assert timeline[0].status == "accepted"


def test_gold_builder_resolves_superseded_currentness_and_validity() -> None:
    decisions = [
        SilverDecision(
            id="decision_old",
            corpus_id="openclaw",
            title="GraphRAG adoption",
            status="proposed",
            decision_date="2026-06-01",
            source_ids=["bronze_old"],
            confidence=0.8,
        ),
        SilverDecision(
            id="decision_new",
            corpus_id="openclaw",
            title="LightRAG adoption",
            status="accepted",
            decision_date="2026-06-09",
            supersedes=["GraphRAG adoption"],
            source_ids=["bronze_new"],
            confidence=0.9,
        ),
    ]

    _, edges, timeline = GoldBuilder().build([], [], decisions)
    by_title = {event.title: event for event in timeline}

    assert ("LightRAG adoption", "SUPERSEDES", "GraphRAG adoption") in {
        (edge.source, edge.relation, edge.target) for edge in edges
    }
    assert by_title["GraphRAG adoption"].current is False
    assert by_title["GraphRAG adoption"].valid_to == "2026-06-09"
    assert by_title["GraphRAG adoption"].superseded_by == ["LightRAG adoption"]
    assert by_title["LightRAG adoption"].current is True
    assert by_title["LightRAG adoption"].supersedes == ["GraphRAG adoption"]
