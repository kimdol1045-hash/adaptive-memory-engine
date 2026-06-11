import json
import stat
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ame.bronze.store import BronzeStore
from ame.cli.main import app
from ame.connectors.google import GmailConnector
from ame.connectors.google_oauth import GoogleOAuthClient, GoogleOAuthConfig, GoogleOAuthError, GoogleTokenStore, exchange_and_save_google_token
from ame.core.corpus import create_corpus, require_corpus
from ame.core.paths import ensure_runtime_layout
from ame.hermes.memory import HermesMemoryStore
from ame.pipeline import MemoryPipeline
from ame.security import redact_secrets


class FakeGoogleHttp:
    def post_json(self, url: str, data: dict, headers: dict | None = None) -> dict:
        assert url == "https://oauth2.googleapis.com/token"
        assert data["grant_type"] == "authorization_code"
        return {
            "access_token": "ya29.test",
            "refresh_token": "refresh-test",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/gmail.readonly",
        }


def test_google_drive_gmail_calendar_sheets_ingest_and_personal_import(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    create_corpus("google")

    drive = tmp_path / "drive.json"
    drive.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "id": "doc-1",
                        "name": "Hermes Memory Plan",
                        "text": "Decision: Google Drive Connector will preserve original document URLs.",
                        "folder": "Chronicle/Specs",
                        "webViewLink": "https://docs.google.com/document/d/doc-1",
                        "modifiedTime": "2026-06-09T10:00:00Z",
                        "owners": [{"emailAddress": "andan@example.com"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    gmail = tmp_path / "gmail.json"
    gmail.write_text(
        json.dumps(
            {
                "threads": [
                    {
                        "threadId": "thr-1",
                        "subject": "Connector next action",
                        "messages": [
                            {
                                "id": "msg-1",
                                "from": "alice@example.com",
                                "to": "andan@example.com",
                                "labelIds": ["INBOX", "IMPORTANT"],
                                "date": "2026-06-09T11:00:00Z",
                                "body": "Next action is to connect Gmail threads to Hermes personal memory.",
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    calendar = tmp_path / "calendar.json"
    calendar.write_text(
        json.dumps(
            {
                "events": [
                    {
                        "id": "evt-1",
                        "calendar_id": "primary",
                        "summary": "AME connector review",
                        "start": {"dateTime": "2026-06-09T12:00:00+09:00"},
                        "end": {"dateTime": "2026-06-09T12:30:00+09:00"},
                        "attendees": [{"email": "andan@example.com"}, {"email": "alice@example.com"}],
                        "htmlLink": "https://calendar.google.com/event?eid=evt-1",
                        "location": "Google Meet",
                        "description": "Review Google Calendar Connector as Meeting memory.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    sheets = tmp_path / "sheets.json"
    sheets.write_text(
        json.dumps(
            {
                "spreadsheet_id": "sheet-1",
                "sheet_name": "Roadmap",
                "url": "https://docs.google.com/spreadsheets/d/sheet-1",
                "rows": [
                    {
                        "row_index": 7,
                        "title": "Connector status",
                        "values": {"Project": "AME", "Status": "Google Sheets Connector planned"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    pipeline = MemoryPipeline()
    assert pipeline.ingest("google", drive, profile="drive").documents == 1
    assert pipeline.ingest("google", gmail, profile="gmail").documents == 2
    assert pipeline.ingest("google", calendar, profile="calendar").documents == 3
    assert pipeline.ingest("google", sheets, profile="sheets").documents == 4

    docs = list(BronzeStore(require_corpus("google")).list())
    by_source = {doc.source_id: doc for doc in docs}

    assert by_source["google_drive:doc-1"].metadata["original_url"] == "https://docs.google.com/document/d/doc-1"
    assert by_source["google_drive:doc-1"].metadata["folder"] == "Chronicle/Specs"
    assert by_source["google_drive:doc-1"].metadata["occurred_at"] == "2026-06-09T10:00:00Z"
    assert by_source["gmail:thr-1"].metadata["memory_type"] == "Email"
    assert by_source["gmail:thr-1"].metadata["message_ids"] == ["msg-1"]
    assert by_source["gmail:thr-1"].metadata["labels"] == ["INBOX", "IMPORTANT"]
    assert by_source["gmail:thr-1"].metadata["occurred_at"] == "2026-06-09T11:00:00Z"
    assert "Message ID: msg-1" in by_source["gmail:thr-1"].content
    assert by_source["google_calendar:primary:evt-1"].metadata["memory_type"] == "Meeting"
    assert by_source["google_calendar:primary:evt-1"].metadata["location"] == "Google Meet"
    assert by_source["google_calendar:primary:evt-1"].metadata["occurred_at"] == "2026-06-09T12:00:00+09:00"
    assert by_source["google_sheets:sheet-1:Roadmap:7"].metadata["sheet_name"] == "Roadmap"

    imported = HermesMemoryStore("google").import_bronze(docs)
    imported_types = {memory.source_id: memory.type for memory in imported}

    assert imported_types["google_drive:doc-1"] == "Document"
    assert imported_types["gmail:thr-1"] == "Email"
    assert imported_types["google_calendar:primary:evt-1"] == "Meeting"
    assert imported_types["google_sheets:sheet-1:Roadmap:7"] == "Document"


def test_google_oauth_url_exchange_and_cli_profile(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    config = GoogleOAuthConfig(client_id="client-1", client_secret="secret-1", redirect_uri="http://localhost/callback")
    auth_url = GoogleOAuthClient(config).authorization_url("state-1")
    store_path = tmp_path / "tokens" / "google.json"

    token = exchange_and_save_google_token("code-1", config, account_id="andan", store_path=store_path, http=FakeGoogleHttp())
    loaded = GoogleTokenStore(store_path).load("andan")
    runner = CliRunner()
    profiles = runner.invoke(app, ["connectors", "profiles"])

    assert "accounts.google.com" in auth_url
    assert "access_type=offline" in auth_url
    assert token.refresh_token == "refresh-test"
    assert loaded.access_token == "ya29.test"
    assert stat.S_IMODE(store_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(store_path.parent.stat().st_mode) == 0o700
    assert redact_secrets(token.model_dump(mode="json"))["access_token"] == "[redacted]"
    assert redact_secrets(token.model_dump(mode="json"))["refresh_token"] == "[redacted]"
    assert GoogleTokenStore(store_path).revoke("andan") is True
    with pytest.raises(GoogleOAuthError):
        GoogleTokenStore(store_path).load("andan")
    assert profiles.exit_code == 0
    assert "google-drive-json" in profiles.output
    assert "google-oauth" in profiles.output


def test_google_connector_pii_redaction_modes(tmp_path: Path) -> None:
    gmail = tmp_path / "gmail.json"
    gmail.write_text(
        json.dumps(
            {
                "threads": [
                    {
                        "threadId": "thr-privacy",
                        "subject": "Private planning",
                        "messages": [
                            {
                                "from": "alice@example.com",
                                "to": "andan@example.com",
                                "body": "Call +1 555-010-9999 and email alice@example.com.",
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    ref = GmailConnector(pii_redaction="content").scan(gmail)[0]

    assert "alice@example.com" not in ref.content
    assert "+1 555-010-9999" not in ref.content
    assert ref.metadata["participants"] == ["[email]", "[email]"]
    assert ref.metadata["pii_redaction"] == "content"
