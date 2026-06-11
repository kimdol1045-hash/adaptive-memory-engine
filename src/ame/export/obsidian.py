from __future__ import annotations

from pathlib import Path

from ame.gold.schema import GoldEdge, GoldNode, GoldTimelineEvent
from ame.gold.store import GoldStore


class ObsidianExporter:
    def __init__(self, gold: GoldStore):
        self.gold = gold

    def export(self, output_dir: Path) -> int:
        output_dir.mkdir(parents=True, exist_ok=True)
        nodes = self.gold.nodes()
        edges = self.gold.edges()
        timeline_by_title = {event.title.casefold(): event for event in self.gold.timeline()}
        count = 0
        for node in nodes:
            path = self._node_path(output_dir, node)
            path.parent.mkdir(parents=True, exist_ok=True)
            event = timeline_by_title.get(node.name.casefold()) if node.type == "Decision" else None
            note = self._decision_note(node, event, edges) if event else self._node_note(node, edges)
            path.write_text(note, encoding="utf-8")
            count += 1
        (output_dir / "Index.md").write_text(self._index_note(nodes), encoding="utf-8")
        count += 1
        return count

    def _node_note(self, node: GoldNode, edges: list[GoldEdge]) -> str:
        lines = [
            "---",
            f"type: {node.type}",
            f"canonical_name: {node.canonical_name}",
            "---",
            "",
            f"# {node.name}",
            "",
            "## Relations",
            *self._relation_lines(node, edges),
            "",
            "## Sources",
            *[f"- {source_id}" for source_id in node.source_ids],
            "",
        ]
        return "\n".join(lines)

    def _decision_note(self, node: GoldNode, event: GoldTimelineEvent, edges: list[GoldEdge]) -> str:
        project = event.project or self._edge_target(node.name, "MADE_IN", edges)
        tools = [edge.target for edge in edges if edge.source == node.name and edge.relation == "USES"]
        related_decisions = [edge.target for edge in edges if edge.source == node.name and edge.relation == "SUPERSEDES"]
        lines = [
            "---",
            "type: Decision",
            f"canonical_name: {node.canonical_name}",
            f"status: {event.status or 'unknown'}",
            "---",
            "",
            f"# {node.name}",
            "",
            f"Status: {event.status or 'unknown'}",
            f"Project: {self._link('Project', project) if project else 'n/a'}",
            "",
            "## Summary",
            "",
            event.rationale or node.name,
            "",
            "## Related Tools",
            *[f"- {self._link('Tool', tool)}" for tool in tools],
            "",
            "## Sources",
            *[f"- {source_id}" for source_id in node.source_ids],
            "",
            "## Related Decisions",
            *[f"- {self._link('Decision', title)}" for title in related_decisions],
            "",
            "## Relations",
            *self._relation_lines(node, edges),
            "",
        ]
        return "\n".join(lines)

    def _index_note(self, nodes: list[GoldNode]) -> str:
        lines = ["# Memory Index", ""]
        for node_type in sorted({node.type for node in nodes}):
            lines.extend([f"## {self._folder_name(node_type)}", ""])
            for node in sorted((node for node in nodes if node.type == node_type), key=lambda row: row.name.casefold()):
                lines.append(f"- {self._link(node.type, node.name)}")
            lines.append("")
        return "\n".join(lines)

    def _node_path(self, output_dir: Path, node: GoldNode) -> Path:
        return output_dir / self._folder_name(node.type) / f"{self._safe_name(node.name)}.md"

    def _folder_name(self, node_type: str) -> str:
        return {
            "Project": "Projects",
            "Tool": "Tools",
            "Decision": "Decisions",
            "Person": "People",
            "Concept": "Concepts",
        }.get(node_type, f"{node_type}s")

    def _link(self, node_type: str, name: str) -> str:
        return f"[[{self._folder_name(node_type)}/{self._safe_name(name)}|{name}]]"

    def _safe_name(self, name: str) -> str:
        return name.replace("/", "-").replace(":", " -").strip()

    def _edge_target(self, source: str, relation: str, edges: list[GoldEdge]) -> str | None:
        for edge in edges:
            if edge.source == source and edge.relation == relation:
                return edge.target
        return None

    def _relation_lines(self, node: GoldNode, edges: list[GoldEdge]) -> list[str]:
        lines: list[str] = []
        for edge in edges:
            if edge.source == node.name:
                lines.append(f"- {edge.relation}: {edge.target}")
            elif edge.target == node.name:
                lines.append(f"- {edge.relation}: {edge.source}")
        return lines or ["- n/a"]
