from ame.bronze.schema import BronzeDocument
from ame.silver.llm_extractor import LlmExtractor


class FakeClient:
    def complete_json(self, prompt: str, payload: dict) -> dict:
        return {
            "entities": [
                {"type": "Project", "name": "OpenClaw", "span": "OpenClaw", "confidence": 0.9},
                {"type": "Tool", "name": "LightRAG", "span": "LightRAG", "confidence": 0.9},
            ],
            "relations": [
                {"subject": "OpenClaw", "predicate": "USES", "object": "LightRAG", "confidence": 0.9}
            ],
            "decisions": [
                {"title": "LightRAG adoption", "status": "accepted", "project": "OpenClaw", "confidence": 0.8}
            ],
        }


class RetryClient:
    def __init__(self) -> None:
        self.calls = 0

    def complete_json(self, prompt: str, payload: dict) -> dict:
        self.calls += 1
        if self.calls == 1:
            return {"entities": [{"type": "BadType", "name": "OpenClaw", "confidence": 0.9}]}
        return {
            "entities": [{"type": "Project", "name": "OpenClaw", "span": "OpenClaw", "confidence": 0.9}],
            "relations": [],
            "decisions": [],
        }


class InvalidEntityClient:
    def complete_json(self, prompt: str, payload: dict) -> dict:
        return {"entities": [{"type": "BadType", "name": "OpenClaw", "confidence": 0.9}]}


class InvalidDecisionStatusClient:
    def complete_json(self, prompt: str, payload: dict) -> dict:
        return {
            "entities": [{"type": "Tool", "name": "LightRAG", "span": "LightRAG", "confidence": 0.9}],
            "relations": [],
            "decisions": [{"title": "Schema required field", "status": "required", "confidence": 0.8}],
        }


def bronze_doc() -> BronzeDocument:
    return BronzeDocument(
        id="bronze_1",
        corpus_id="openclaw",
        source_type="markdown",
        source_id="openclaw.md",
        content="OpenClaw decided to use LightRAG.",
        metadata={"frontmatter": {"project": "OpenClaw"}, "headings": [], "wikilinks": [], "tags": []},
        content_hash="sha256:x",
    )


def test_llm_extractor_parses_client_json() -> None:
    doc = bronze_doc()

    entities, relations, decisions = LlmExtractor(FakeClient()).extract(doc)

    assert {entity.name for entity in entities} >= {"OpenClaw", "LightRAG"}
    assert [(relation.subject, relation.predicate, relation.object) for relation in relations] == [("OpenClaw", "USES", "LightRAG")]
    assert decisions[-1].title == "LightRAG adoption"


def test_llm_extractor_retries_invalid_schema() -> None:
    client = RetryClient()

    entities, _, _ = LlmExtractor(client, max_retries=1).extract(bronze_doc())

    assert client.calls == 2
    assert any(entity.name == "OpenClaw" for entity in entities)


def test_llm_extractor_skips_invalid_rows_after_schema_retry_exhausted() -> None:
    entities, relations, decisions = LlmExtractor(InvalidEntityClient(), max_retries=0).extract(bronze_doc())

    assert entities
    assert relations
    assert decisions


def test_llm_extractor_skips_invalid_decision_status_without_failing_document() -> None:
    entities, relations, decisions = LlmExtractor(InvalidDecisionStatusClient(), max_retries=0).extract(bronze_doc())

    assert any(entity.name == "LightRAG" for entity in entities)
    assert all(decision.status in {"proposed", "accepted", "rejected", "superseded"} for decision in decisions)
    assert all(decision.title != "Schema required field" for decision in decisions)
