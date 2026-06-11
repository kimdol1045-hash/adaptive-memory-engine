from pathlib import Path

from ame.bronze.store import BronzeStore
from ame.connectors.obsidian import ObsidianConnector
from ame.gold.schema import GoldEdge, GoldNode, GoldTimelineEvent
from ame.gold.store import GoldStore
from ame.query.engine import QueryEngine


def test_query_result_includes_sources(tmp_path: Path) -> None:
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "openclaw.md").write_text("OpenClaw decided to use LightRAG.", encoding="utf-8")
    corpus_root = tmp_path / "corpus"
    connector = ObsidianConnector()
    doc = connector.load("openclaw", connector.scan(notes)[0])
    BronzeStore(corpus_root).put(doc)
    GoldStore(corpus_root).replace(
        [GoldNode(id="node_1", corpus_id="openclaw", type="Tool", name="LightRAG", canonical_name="lightrag", source_ids=[doc.id])],
        [GoldEdge(id="edge_1", corpus_id="openclaw", source="OpenClaw", relation="USES", target="LightRAG", source_ids=[doc.id])],
    )

    result = QueryEngine(BronzeStore(corpus_root), GoldStore(corpus_root)).query("LightRAG")

    assert result.sources[0].document == "openclaw.md"
    assert result.confidence is not None


def test_query_result_uses_decision_timeline(tmp_path: Path) -> None:
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "openclaw.md").write_text("OpenClaw decided to use LightRAG.", encoding="utf-8")
    corpus_root = tmp_path / "corpus"
    connector = ObsidianConnector()
    doc = connector.load("openclaw", connector.scan(notes)[0])
    BronzeStore(corpus_root).put(doc)
    GoldStore(corpus_root).replace(
        [
            GoldNode(id="node_project", corpus_id="openclaw", type="Project", name="OpenClaw", canonical_name="openclaw", source_ids=[doc.id]),
            GoldNode(id="node_tool", corpus_id="openclaw", type="Tool", name="LightRAG", canonical_name="lightrag", source_ids=[doc.id]),
            GoldNode(
                id="node_decision",
                corpus_id="openclaw",
                type="Decision",
                name="LightRAG adoption",
                canonical_name="lightrag adoption",
                source_ids=[doc.id],
            ),
        ],
        [
            GoldEdge(id="edge_uses", corpus_id="openclaw", source="LightRAG adoption", relation="USES", target="LightRAG", source_ids=[doc.id]),
        ],
        [
            GoldTimelineEvent(
                id="timeline_1",
                corpus_id="openclaw",
                event_type="decision",
                title="LightRAG adoption",
                status="accepted",
                project="OpenClaw",
                source_ids=[doc.id],
            )
        ],
    )

    result = QueryEngine(BronzeStore(corpus_root), GoldStore(corpus_root)).query("OpenClaw에서 뭘 결정했지?")

    assert "Decision: LightRAG adoption" in result.answer
    assert result.sources[0].document == "openclaw.md"
