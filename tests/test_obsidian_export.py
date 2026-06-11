from pathlib import Path

from ame.export.obsidian import ObsidianExporter
from ame.gold.schema import GoldEdge, GoldNode, GoldTimelineEvent
from ame.gold.store import GoldStore


def test_obsidian_export_writes_typed_vault_and_decision_note(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    gold = GoldStore(corpus_root)
    gold.replace(
        [
            GoldNode(id="node_project", corpus_id="openclaw", type="Project", name="OpenClaw", canonical_name="openclaw", source_ids=["bronze_1"]),
            GoldNode(id="node_tool", corpus_id="openclaw", type="Tool", name="LightRAG", canonical_name="lightrag", source_ids=["bronze_1"]),
            GoldNode(
                id="node_decision",
                corpus_id="openclaw",
                type="Decision",
                name="LightRAG adoption",
                canonical_name="lightrag adoption",
                source_ids=["bronze_1"],
            ),
        ],
        [
            GoldEdge(id="edge_made_in", corpus_id="openclaw", source="LightRAG adoption", relation="MADE_IN", target="OpenClaw", source_ids=["bronze_1"]),
            GoldEdge(id="edge_uses", corpus_id="openclaw", source="LightRAG adoption", relation="USES", target="LightRAG", source_ids=["bronze_1"]),
        ],
        [
            GoldTimelineEvent(
                id="timeline_1",
                corpus_id="openclaw",
                event_type="decision",
                title="LightRAG adoption",
                status="accepted",
                project="OpenClaw",
                rationale="Use LightRAG as the storage core.",
                source_ids=["bronze_1"],
                confidence=0.8,
            )
        ],
    )

    output_dir = tmp_path / "vault"
    count = ObsidianExporter(gold).export(output_dir)

    decision_note = output_dir / "Decisions" / "LightRAG adoption.md"
    assert count == 4
    assert (output_dir / "Projects" / "OpenClaw.md").exists()
    assert (output_dir / "Tools" / "LightRAG.md").exists()
    assert (output_dir / "Index.md").exists()
    assert decision_note.exists()
    content = decision_note.read_text(encoding="utf-8")
    assert "Status: accepted" in content
    assert "[[Projects/OpenClaw|OpenClaw]]" in content
    assert "[[Tools/LightRAG|LightRAG]]" in content
