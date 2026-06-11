from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from ame.bronze.schema import BronzeDocument
from ame.bronze.store import BronzeStore
from ame.connectors.markdown import MarkdownConnector
from ame.core.corpus import require_corpus
from ame.gold.builder import GoldBuilder
from ame.gold.store import GoldStore
from ame.silver.extractor import DeterministicExtractor
from ame.silver.rationale import RationaleExtractor
from ame.silver.schema import SilverDecision, SilverEntity, SilverRelation
from ame.silver.store import SilverStore
from ame.storage.lightrag_adapter import LightRagAdapter


class MemoryWriter:
    def write_decision(
        self,
        corpus_id: str,
        title: str,
        rationale: str,
        project: str | None = None,
        status: str = "accepted",
        participants: list[str] | None = None,
        source: str = "writeback",
    ) -> Path:
        corpus_root = require_corpus(corpus_id)
        path = corpus_root / "writeback" / "decisions" / f"{self._safe_filename(title)}.md"
        participants = participants or []
        date = datetime.now(timezone.utc).date().isoformat()
        frontmatter = ["---", f'title: "{title}"', f"date: {date}", f"source: {source}"]
        if project:
            frontmatter.append(f"project: {project}")
        frontmatter.append("---")
        content = "\n".join(
            [
                *frontmatter,
                "",
                f"# {title}",
                "",
                f"{title} 결정했다.",
                "",
                "## Rationale",
                rationale,
                "",
                "## Participants",
                *[f"- {participant}" for participant in participants],
                "",
            ]
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        decision = SilverDecision(
            id=self._id("decision", corpus_id, title, date),
            corpus_id=corpus_id,
            title=title,
            status=status,  # type: ignore[arg-type]
            project=project,
            rationale=rationale,
            decision_date=date,
            participants=participants,
            source_ids=[],
            confidence=0.95,
        )
        self._append_markdown_file(corpus_id, path, explicit_decision=decision)
        return path

    def write_note(self, corpus_id: str, title: str, content: str, source: str = "writeback") -> Path:
        corpus_root = require_corpus(corpus_id)
        path = corpus_root / "writeback" / "notes" / f"{self._safe_filename(title)}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(["---", f'title: "{title}"', f"source: {source}", "---", "", f"# {title}", "", content, ""]),
            encoding="utf-8",
        )
        self._append_markdown_file(corpus_id, path)
        return path

    def _append_markdown_file(self, corpus_id: str, path: Path, explicit_decision: SilverDecision | None = None) -> None:
        corpus_root = require_corpus(corpus_id)
        connector = MarkdownConnector()
        ref = connector.scan(path)[0]
        doc = BronzeStore(corpus_root).put(connector.load(corpus_id, ref))

        entities, relations, decisions = DeterministicExtractor().extract(doc)
        if explicit_decision:
            explicit_decision.source_ids = [doc.id]
            decisions = [decision for decision in decisions if decision.title.casefold() != explicit_decision.title.casefold()]
            decisions.append(explicit_decision)
            entities.append(
                SilverEntity(
                    id=f"entity_{explicit_decision.id}",
                    corpus_id=corpus_id,
                    type="Decision",
                    name=explicit_decision.title,
                    span=explicit_decision.title if explicit_decision.title in doc.content else None,
                    source_ids=[doc.id],
                    confidence=explicit_decision.confidence,
                )
            )
            if explicit_decision.project:
                entities.append(
                    SilverEntity(
                        id=self._id("entity", corpus_id, "Project", explicit_decision.project),
                        corpus_id=corpus_id,
                        type="Project",
                        name=explicit_decision.project,
                        span=explicit_decision.project if explicit_decision.project in doc.content else None,
                        source_ids=[doc.id],
                        confidence=0.95,
                    )
                )

        silver = SilverStore(corpus_root)
        all_entities = self._dedupe_entities(silver.entities() + entities)
        all_relations = self._dedupe_relations(silver.relations() + relations)
        all_decisions = self._dedupe_decisions(silver.decisions() + decisions)
        all_docs = list(BronzeStore(corpus_root).list())
        all_rationales = RationaleExtractor().extract(all_docs, all_decisions)
        silver.replace(all_entities, all_relations, all_decisions, [], all_rationales)
        nodes, edges, timeline = GoldBuilder().build(all_entities, all_relations, all_decisions, all_rationales)
        GoldStore(corpus_root).replace(nodes, edges, timeline)
        LightRagAdapter(corpus_root).sync(nodes, edges, all_docs)

    def _dedupe_entities(self, entities: list[SilverEntity]) -> list[SilverEntity]:
        by_key: dict[tuple[str, str], SilverEntity] = {}
        for entity in entities:
            key = (entity.type, entity.name.casefold())
            existing = by_key.get(key)
            if existing:
                existing.source_ids = sorted(set(existing.source_ids + entity.source_ids))
                existing.confidence = max(existing.confidence, entity.confidence)
                continue
            by_key[key] = entity
        return list(by_key.values())

    def _dedupe_relations(self, relations: list[SilverRelation]) -> list[SilverRelation]:
        by_key: dict[tuple[str, str, str], SilverRelation] = {}
        for relation in relations:
            key = (relation.subject.casefold(), relation.predicate, relation.object.casefold())
            existing = by_key.get(key)
            if existing:
                existing.source_ids = sorted(set(existing.source_ids + relation.source_ids))
                existing.confidence = max(existing.confidence, relation.confidence)
                continue
            by_key[key] = relation
        return list(by_key.values())

    def _dedupe_decisions(self, decisions: list[SilverDecision]) -> list[SilverDecision]:
        by_title: dict[str, SilverDecision] = {}
        for decision in decisions:
            key = decision.title.casefold()
            existing = by_title.get(key)
            if existing:
                existing.source_ids = sorted(set(existing.source_ids + decision.source_ids))
                existing.confidence = max(existing.confidence, decision.confidence)
                if not existing.rationale:
                    existing.rationale = decision.rationale
                continue
            by_title[key] = decision
        return list(by_title.values())

    def _safe_filename(self, value: str) -> str:
        return re.sub(r"[^0-9A-Za-z가-힣._ -]+", "-", value).strip(" .-")[:120] or "memory"

    def _id(self, prefix: str, *parts: str) -> str:
        digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
        return f"{prefix}_{digest}"
