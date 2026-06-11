import json
from pathlib import Path

from ame.core.corpus import create_corpus, require_corpus
from ame.core.paths import ensure_runtime_layout
from ame.pipeline import MemoryPipeline
from ame.bronze.store import BronzeStore


def test_slack_export_connector_ingests_messages(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    create_corpus("slack")
    channel = tmp_path / "slack" / "architecture"
    channel.mkdir(parents=True)
    (channel / "2026-06-09.json").write_text(
        json.dumps([{"ts": "1717890000.0001", "user": "andan", "text": "OpenClaw decided to use LightRAG for memory."}]),
        encoding="utf-8",
    )

    report = MemoryPipeline().ingest("slack", tmp_path / "slack", profile="slack-export")
    docs = list(BronzeStore(require_corpus("slack")).list())

    assert report.documents == 1
    assert docs[0].source_type == "slack"
    assert "OpenClaw decided to use LightRAG" in docs[0].content


def test_jira_connector_ingests_issues_and_comments(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    create_corpus("jira")
    data = {
        "issues": [
            {
                "key": "AME-12",
                "fields": {
                    "summary": "Memory API 결정",
                    "description": "OpenClaw decided to expose memory.retrieve and memory.graph.",
                    "comments": [{"body": "CLI parity도 필요하다."}],
                },
            }
        ]
    }
    source = tmp_path / "jira.json"
    source.write_text(json.dumps(data), encoding="utf-8")

    report = MemoryPipeline().ingest("jira", source, profile="jira")
    docs = list(BronzeStore(require_corpus("jira")).list())

    assert report.documents == 1
    assert docs[0].source_type == "jira"
    assert "AME-12" in docs[0].source_id
    assert "CLI parity" in docs[0].content


def test_github_connector_ingests_issues_prs_and_discussions(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    create_corpus("github")
    rows = [
        {
            "number": 42,
            "kind": "pull_request",
            "title": "Add Memory SDK",
            "body": "We decided to add Corpus.retrieve and Corpus.graph.",
            "comments": [{"body": "This supports OpenClaw agent usage."}],
        }
    ]
    source = tmp_path / "github.json"
    source.write_text(json.dumps(rows), encoding="utf-8")

    report = MemoryPipeline().ingest("github", source, profile="github")
    docs = list(BronzeStore(require_corpus("github")).list())

    assert report.documents == 1
    assert docs[0].source_type == "github"
    assert "pull_request" in docs[0].source_id
    assert "Corpus.retrieve" in docs[0].content


def test_notion_connector_ingests_pages(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    create_corpus("notion")
    rows = [
        {
            "id": "page-1",
            "title": "Chronicle 기억 설계",
            "content": "Decision: Notion pages should become document memory.",
            "url": "https://notion.so/page-1",
            "last_edited_time": "2026-06-09T01:00:00Z",
        }
    ]
    source = tmp_path / "notion.json"
    source.write_text(json.dumps(rows), encoding="utf-8")

    report = MemoryPipeline().ingest("notion", source, profile="notion")
    docs = list(BronzeStore(require_corpus("notion")).list())

    assert report.documents == 1
    assert docs[0].source_type == "notion"
    assert "page-1" in docs[0].source_id
    assert "Notion pages" in docs[0].content
