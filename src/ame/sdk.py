from __future__ import annotations

from pathlib import Path

from ame.agent.memory_api import AgentMemoryAPI
from ame.core.corpus import create_corpus, require_corpus
from ame.pipeline import IngestReport, MemoryPipeline
from ame.query.result import QueryResult


class Corpus:
    def __init__(self, corpus_id: str, create: bool = False):
        self.corpus_id = corpus_id
        self.root = create_corpus(corpus_id) if create else require_corpus(corpus_id)
        self.memory = AgentMemoryAPI(self.root)

    def ingest(self, source_path: str | Path, profile: str | None = None) -> IngestReport:
        return MemoryPipeline().ingest(self.corpus_id, Path(source_path), profile=profile)

    def query(self, question: str, mode: str = "hybrid") -> QueryResult:
        return self.memory.search(question)

    def retrieve(self, query: str, k: int = 8):
        return self.memory.retrieve(query, k=k)

    def graph(self, entity: str):
        return self.memory.graph(entity)

    def timeline(self, entity: str | None = None):
        return self.memory.timeline(entity)

    def decisions(
        self,
        project: str | None = None,
        current_only: bool = True,
        date_from: str | None = None,
        date_to: str | None = None,
    ):
        return self.memory.decisions(project=project, current_only=current_only, date_from=date_from, date_to=date_to)

    def write_decision(
        self,
        title: str,
        rationale: str,
        project: str | None = None,
        participants: list[str] | None = None,
        source: str = "writeback",
    ):
        return self.memory.write_decision(title, rationale, project=project, participants=participants, source=source)

    def write_note(self, title: str, content: str):
        return self.memory.write_note(title, content)
