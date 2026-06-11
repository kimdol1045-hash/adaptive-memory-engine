from __future__ import annotations

from pathlib import Path

from ame.bronze.store import BronzeStore
from ame.gold.resolver import SupersedesResolver
from ame.gold.store import GoldStore
from ame.query.diff import MemoryDiff, MemoryDiffEngine
from ame.query.engine import QueryEngine
from ame.query.mql import MqlEngine, MqlResult
from ame.query.result import QueryResult
from ame.silver.store import SilverStore
from ame.agent.results import DecisionsResult, GraphResult, RetrieveResult, WriteResult
from ame.writeback import MemoryWriter


class AgentMemoryAPI:
    def __init__(self, corpus_root: Path):
        self.corpus_root = corpus_root
        self.bronze = BronzeStore(corpus_root)
        self.gold = GoldStore(corpus_root)

    def search(self, query: str) -> QueryResult:
        return QueryEngine(self.bronze, self.gold).query(query)

    def retrieve(self, query: str, k: int = 8) -> RetrieveResult:
        normalized = query.casefold()
        matches: list[dict] = []
        for node in self.gold.nodes():
            if normalized in node.name.casefold() or normalized in node.type.casefold():
                matches.append({"kind": "node", **node.model_dump()})
        for edge in self.gold.edges():
            haystack = f"{edge.source} {edge.relation} {edge.target}".casefold()
            if normalized in haystack:
                matches.append({"kind": "edge", **edge.model_dump()})
        for document in self.bronze.list():
            if normalized in document.content.casefold() or normalized in document.source_id.casefold():
                matches.append(
                    {
                        "kind": "document",
                        "id": document.id,
                        "source_id": document.source_id,
                        "source_type": document.source_type,
                        "metadata": document.metadata,
                    }
                )
        return RetrieveResult(query=query, matches=matches[:k])

    def graph(self, entity: str) -> GraphResult:
        normalized = entity.casefold()
        edges = [
            edge
            for edge in self.gold.edges()
            if normalized in edge.source.casefold() or normalized in edge.target.casefold()
        ]
        names = {edge.source.casefold() for edge in edges} | {edge.target.casefold() for edge in edges}
        nodes = [node for node in self.gold.nodes() if node.name.casefold() in names or normalized in node.name.casefold()]
        return GraphResult(
            entity=entity,
            nodes=[node.model_dump() for node in nodes],
            edges=[edge.model_dump() for edge in edges],
        )

    def current_decision(self) -> QueryResult:
        current = [event for event in self._timeline() if event.current and event.status == "accepted"]
        titles = ", ".join(event.title for event in current) or "없음"
        answer = f"현재 current decision은 {titles}이다. superseded decision은 current=false로 제외한다."
        return QueryResult(
            answer=answer,
            matches=[answer],
            sources=[],
            confidence=0.9,
            raw={
                "answer_builder": "agent_memory_api",
                "api": "memory.current_decision",
                "current_decisions": [event.title for event in current],
            },
        )

    def decisions(
        self,
        project: str | None = None,
        current_only: bool = True,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> DecisionsResult:
        events = self._timeline()
        if project:
            events = [event for event in events if event.project and project.casefold() in event.project.casefold()]
        if current_only:
            events = [event for event in events if event.current]
        if date_from:
            events = [event for event in events if event.valid_from and event.valid_from >= date_from]
        if date_to:
            events = [event for event in events if event.valid_from and event.valid_from <= date_to]
        return DecisionsResult(
            project=project,
            current_only=current_only,
            decisions=[event.model_dump() for event in events],
        )

    def timeline(self, project: str | None = None) -> MqlResult:
        suffix = f' FOR project="{project}"' if project else ""
        return MqlEngine().execute(f"SHOW timeline{suffix}", self._timeline())

    def why(self, decision: str) -> MqlResult:
        return MqlEngine().execute(f'WHY decision="{decision}"', self._timeline(), self._rationales())

    def diff(self, days: int = 7) -> MemoryDiff:
        return MemoryDiffEngine().diff_last_days(self._timeline(), days=days)

    def write_decision(
        self,
        title: str,
        rationale: str,
        project: str | None = None,
        participants: list[str] | None = None,
        source: str = "writeback",
    ) -> WriteResult:
        path = MemoryWriter().write_decision(
            self.corpus_root.name,
            title,
            rationale,
            project=project,
            participants=participants,
            source=source,
        )
        return WriteResult(kind="decision", path=str(path), title=title)

    def write_note(self, title: str, content: str) -> WriteResult:
        path = MemoryWriter().write_note(self.corpus_root.name, title, content)
        return WriteResult(kind="note", path=str(path), title=title)

    def mql(self, query: str) -> MqlResult | None:
        return MqlEngine().execute(query, self._timeline(), self._rationales())

    def _timeline(self):
        return SupersedesResolver().resolve(self.gold.timeline(), self.gold.edges())

    def _rationales(self):
        return SilverStore(self.corpus_root).rationales()
