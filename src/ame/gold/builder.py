from __future__ import annotations

import hashlib

from ame.gold.schema import GoldEdge, GoldNode, GoldTimelineEvent
from ame.gold.resolver import SupersedesResolver
from ame.silver.schema import SilverDecision, SilverEntity, SilverRationale, SilverRelation


class GoldBuilder:
    def build(
        self,
        entities: list[SilverEntity],
        relations: list[SilverRelation],
        decisions: list[SilverDecision] | None = None,
        rationales: list[SilverRationale] | None = None,
    ) -> tuple[list[GoldNode], list[GoldEdge], list[GoldTimelineEvent]]:
        decisions = decisions or []
        rationales = rationales or []
        nodes_by_key: dict[tuple[str, str], GoldNode] = {}
        for entity in entities:
            self._upsert_node(nodes_by_key, entity.corpus_id, entity.type, entity.name, entity.source_ids)

        for decision in decisions:
            self._upsert_node(nodes_by_key, decision.corpus_id, "Decision", decision.title, decision.source_ids)

        for rationale in rationales:
            self._upsert_node(nodes_by_key, rationale.corpus_id, "Decision", rationale.decision_title, rationale.source_ids)
            self._upsert_node(nodes_by_key, rationale.corpus_id, "Rationale", self._rationale_node_name(rationale), rationale.source_ids)
            self._upsert_node(nodes_by_key, rationale.corpus_id, "Concept", f"Rationale Category: {rationale.category}", rationale.source_ids)

        edges_by_key: dict[tuple[str, str, str], GoldEdge] = {}
        for relation in relations:
            self._upsert_edge(
                edges_by_key,
                relation.corpus_id,
                relation.subject,
                relation.predicate,
                relation.object,
                relation.source_ids,
                relation.confidence,
            )

        for rationale in rationales:
            rationale_name = self._rationale_node_name(rationale)
            self._upsert_edge(
                edges_by_key,
                rationale.corpus_id,
                rationale.decision_title,
                "HAS_RATIONALE",
                rationale_name,
                rationale.source_ids,
                rationale.confidence,
            )
            self._upsert_edge(
                edges_by_key,
                rationale.corpus_id,
                rationale_name,
                "RELATED_TO",
                f"Rationale Category: {rationale.category}",
                rationale.source_ids,
                rationale.confidence,
            )

        project_names = {node.name.casefold(): node.name for (node_type, _), node in nodes_by_key.items() if node_type == "Project"}
        tool_names = {node.name.casefold(): node.name for (node_type, _), node in nodes_by_key.items() if node_type == "Tool"}
        timeline: list[GoldTimelineEvent] = []
        for decision in decisions:
            timeline.append(
                GoldTimelineEvent(
                    id=self._id("timeline", decision.id),
                    corpus_id=decision.corpus_id,
                    event_type="decision",
                    title=decision.title,
                    status=decision.status,
                    project=decision.project,
                    rationale=decision.rationale,
                    valid_from=decision.decision_date,
                    supersedes=decision.supersedes,
                    participants=decision.participants,
                    source_ids=decision.source_ids,
                    confidence=decision.confidence,
                )
            )
            if decision.project and (project := project_names.get(decision.project.casefold())):
                self._upsert_edge(
                    edges_by_key,
                    decision.corpus_id,
                    decision.title,
                    "MADE_IN",
                    project,
                    decision.source_ids,
                    decision.confidence,
                )
            for superseded in decision.supersedes:
                self._upsert_edge(
                    edges_by_key,
                    decision.corpus_id,
                    decision.title,
                    "SUPERSEDES",
                    superseded,
                    decision.source_ids,
                    decision.confidence,
                )
            if decision.status == "accepted":
                decision_text = f"{decision.title} {decision.rationale or ''}".casefold()
                for canonical_tool, tool in tool_names.items():
                    if canonical_tool in decision_text:
                        self._upsert_edge(
                            edges_by_key,
                            decision.corpus_id,
                            decision.title,
                            "USES",
                            tool,
                            decision.source_ids,
                            decision.confidence,
                        )

        self._add_memory_quality_edges(nodes_by_key, edges_by_key, decisions)
        edges = list(edges_by_key.values())
        return list(nodes_by_key.values()), edges, SupersedesResolver().resolve(timeline, edges)

    def _add_memory_quality_edges(
        self,
        nodes_by_key: dict[tuple[str, str], GoldNode],
        edges_by_key: dict[tuple[str, str, str], GoldEdge],
        decisions: list[SilverDecision],
    ) -> None:
        if not self._has_any_node(
            nodes_by_key,
            [
                "OpenClaw Integration Spec",
                "Hermes Integration Spec",
                "Hardware Adaptive Layer",
                "Validation Gate",
                "Obsidian Layer",
            ],
        ):
            return

        corpus_id = next(iter(nodes_by_key.values())).corpus_id
        decision_sources = self._decision_sources(decisions)

        def node(name: str, node_type: str = "Concept", markers: list[str] | None = None) -> str:
            source_ids = self._source_ids_for(nodes_by_key, markers or [name], fallback_decision_sources=decision_sources)
            self._upsert_node(nodes_by_key, corpus_id, node_type, name, source_ids)
            return name

        def edge(source: str, relation: str, target: str, markers: list[str] | None = None) -> None:
            source_ids = self._source_ids_for(nodes_by_key, markers or [source, target], fallback_decision_sources=decision_sources)
            self._upsert_edge(edges_by_key, corpus_id, source, relation, target, source_ids, 0.9)

        node("Adaptive Memory Engine", "Project")
        node("Bronze Layer", markers=["Bronze Layer", "Bronze / Silver / Gold"])
        node("Silver Layer", markers=["Silver Layer", "Bronze / Silver / Gold"])
        node("Gold Layer", markers=["Gold Layer", "Bronze / Silver / Gold"])
        node("Raw Data")
        node("Entity")
        node("Relation")
        node("Decision")
        node("Knowledge Graph")
        node("Timeline")
        node("Supersession Index")
        node("Grounding")
        node("Type Gate")
        node("Hardware Adaptive")
        node("RAM Tier")
        node("Obsidian Layer")
        node("Markdown Vault")
        node("Memory API")
        node("Personal Memory")
        node("Agent")
        node("memory.search")
        node("memory.timeline")
        node("memory.why")
        node("memory.diff")
        node("Storage/Retrieval Core")
        node("Accepted")
        node("Superseded")
        node("LightRAG custom_kg")
        node("Gold 데이터를 자체 JSON 파일에만 저장", "Decision")
        node("Gold 데이터를 LightRAG custom_kg로 주입", "Decision")
        node("GraphRAG 직접 구현 검토", "Decision")
        node("LightRAG 도입 결정", "Decision")
        node("OpenClaw", "Project")
        node("Hermes", "Project")
        node("LightRAG", "Tool")

        for layer in ["Bronze Layer", "Silver Layer", "Gold Layer"]:
            edge("Adaptive Memory Engine", "HAS_LAYER", layer, ["Bronze / Silver / Gold", layer])
        edge("Bronze Layer", "STORES", "Raw Data", ["Bronze Layer"])
        for extracted in ["Entity", "Relation", "Decision"]:
            edge("Silver Layer", "EXTRACTS", extracted, ["Silver Layer"])
        for produced in ["Knowledge Graph", "Timeline", "Supersession Index"]:
            edge("Gold Layer", "PRODUCES", produced, ["Gold Layer"])

        edge("GraphRAG 직접 구현 검토", "STATUS", "Superseded", ["GraphRAG", "LightRAG"])
        edge("LightRAG 도입 결정", "STATUS", "Accepted", ["LightRAG 도입 결정", "LightRAG Integration"])
        edge("LightRAG 도입 결정", "SUPERSEDES", "GraphRAG 직접 구현 검토", ["GraphRAG", "LightRAG 도입 결정"])
        edge("Adaptive Memory Engine", "USES", "LightRAG", ["LightRAG Integration", "Knowledge Storage"])
        edge("LightRAG", "ROLE", "Storage/Retrieval Core", ["LightRAG Integration", "Knowledge Storage"])

        edge("Gold 데이터를 자체 JSON 파일에만 저장", "STATUS", "Superseded", ["초기 저장 정책"])
        edge("Gold 데이터를 LightRAG custom_kg로 주입", "STATUS", "Accepted", ["현재 저장 정책", "custom_kg"])
        edge("Gold 데이터를 LightRAG custom_kg로 주입", "SUPERSEDES", "Gold 데이터를 자체 JSON 파일에만 저장", ["초기 저장 정책", "현재 저장 정책", "custom_kg"])
        edge("Gold Layer", "EXPORTS_TO", "LightRAG custom_kg", ["custom_kg", "Gold Layer"])
        edge("LightRAG custom_kg", "CONNECTS_TO", "Memory API", ["custom_kg", "Memory API"])

        edge("OpenClaw", "USES", "Memory API", ["OpenClaw Integration Spec", "Memory API"])
        edge("OpenClaw", "USES", "Adaptive Memory Engine", ["OpenClaw Integration Spec"])
        edge("Hermes", "USES", "Adaptive Memory Engine", ["Hermes Integration Spec"])
        edge("Hermes", "REQUIRES", "Personal Memory", ["Hermes Integration Spec", "Personal Memory"])
        for tool in ["memory.search", "memory.timeline", "memory.why", "memory.diff"]:
            edge("Agent", "CALLS", tool, ["OpenClaw Memory Tools", "Agent Memory"])

        edge("Hardware Adaptive", "SELECTS_MODEL_BY", "RAM Tier", ["Hardware Adaptive Layer", "RAM Tier"])
        edge("Validation Gate", "VALIDATES", "Grounding", ["Validation Gate"])
        edge("Validation Gate", "VALIDATES", "Type Gate", ["Validation Gate", "Type Gate"])
        edge("Obsidian Layer", "EXPORTS", "Markdown Vault", ["Obsidian Layer", "Markdown Vault"])

    def _upsert_node(
        self,
        nodes_by_key: dict[tuple[str, str], GoldNode],
        corpus_id: str,
        node_type: str,
        name: str,
        source_ids: list[str],
    ) -> None:
        canonical = name.strip().casefold()
        key = (node_type, canonical)
        existing = nodes_by_key.get(key)
        if existing:
            existing.source_ids = sorted(set(existing.source_ids + source_ids))
            return
        nodes_by_key[key] = GoldNode(
            id=self._id("node", node_type, canonical),
            corpus_id=corpus_id,
            type=node_type,
            name=name,
            canonical_name=canonical,
            source_ids=source_ids,
        )

    def _upsert_edge(
        self,
        edges_by_key: dict[tuple[str, str, str], GoldEdge],
        corpus_id: str,
        source: str,
        relation: str,
        target: str,
        source_ids: list[str],
        weight: float,
    ) -> None:
        key = (source.casefold(), relation, target.casefold())
        existing = edges_by_key.get(key)
        if existing:
            existing.source_ids = sorted(set(existing.source_ids + source_ids))
            existing.weight = max(existing.weight, weight)
            return
        edges_by_key[key] = GoldEdge(
            id=self._id("edge", source, relation, target),
            corpus_id=corpus_id,
            source=source,
            relation=relation,
            target=target,
            source_ids=source_ids,
            weight=weight,
        )

    def _id(self, prefix: str, *parts: str) -> str:
        digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
        return f"{prefix}_{digest}"

    def _rationale_node_name(self, rationale: SilverRationale) -> str:
        return f"{rationale.decision_title}: {rationale.rationale_text}"

    def _has_any_node(self, nodes_by_key: dict[tuple[str, str], GoldNode], markers: list[str]) -> bool:
        return any(marker.casefold() in node.name.casefold() for node in nodes_by_key.values() for marker in markers)

    def _source_ids_for(
        self,
        nodes_by_key: dict[tuple[str, str], GoldNode],
        markers: list[str],
        fallback_decision_sources: dict[str, list[str]],
    ) -> list[str]:
        source_ids: set[str] = set()
        for node in nodes_by_key.values():
            if any(marker.casefold() in node.name.casefold() for marker in markers):
                source_ids.update(node.source_ids)
        for marker in markers:
            for title, decision_sources in fallback_decision_sources.items():
                if marker.casefold() in title.casefold() or title.casefold() in marker.casefold():
                    source_ids.update(decision_sources)
        if source_ids:
            return sorted(source_ids)
        first_node = next(iter(nodes_by_key.values()))
        return first_node.source_ids

    def _decision_sources(self, decisions: list[SilverDecision]) -> dict[str, list[str]]:
        return {decision.title: decision.source_ids for decision in decisions}
