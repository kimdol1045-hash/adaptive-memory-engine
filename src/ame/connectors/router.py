from __future__ import annotations

from pathlib import Path

from ame.connectors.base import Connector
from ame.connectors.contract import ConnectorProfile, ExportConnectorRuntime
from ame.connectors.github import GitHubConnector
from ame.connectors.google import GmailConnector, GoogleCalendarConnector, GoogleDriveConnector, GoogleSheetsConnector
from ame.connectors.jira import JiraConnector
from ame.connectors.markdown import MarkdownConnector
from ame.connectors.notion import NotionConnector
from ame.connectors.obsidian import ObsidianConnector
from ame.connectors.slack import SlackExportConnector
from ame.core.config import load_config


class ConnectorRouter:
    def profiles(self) -> list[ConnectorProfile]:
        return [
            ConnectorProfile(
                name="markdown",
                source_type="markdown",
                features=["file", "section", "frontmatter", "headings"],
            ),
            ConnectorProfile(
                name="obsidian",
                source_type="obsidian",
                features=["vault_import", "vault_export", "wikilink", "tag"],
            ),
            ConnectorProfile(
                name="slack-export",
                source_type="slack",
                features=["workspace", "channel", "thread", "message", "export_json"],
            ),
            ConnectorProfile(
                name="jira-json",
                source_type="jira",
                features=["issue", "comment", "status", "export_json"],
            ),
            ConnectorProfile(
                name="github-json",
                source_type="github",
                features=["issue", "pull_request", "discussion", "comment", "export_json"],
            ),
            ConnectorProfile(
                name="notion-json",
                source_type="notion",
                features=["page", "database", "block", "comment", "export_json"],
            ),
            ConnectorProfile(
                name="google-drive-json",
                source_type="google_drive",
                features=["file", "document", "owner", "modified_time", "original_url", "export_json"],
            ),
            ConnectorProfile(
                name="gmail-json",
                source_type="gmail",
                features=["thread", "message", "participants", "original_url", "export_json"],
            ),
            ConnectorProfile(
                name="google-calendar-json",
                source_type="google_calendar",
                features=["event", "meeting", "attendees", "time_range", "original_url", "export_json"],
            ),
            ConnectorProfile(
                name="google-sheets-json",
                source_type="google_sheets",
                features=["spreadsheet", "sheet", "row", "modified_time", "original_url", "export_json"],
            ),
            ConnectorProfile(
                name="slack-oauth",
                source_type="slack",
                mode="live",
                features=["workspace", "channel", "thread", "message", "incremental_sync"],
            ),
            ConnectorProfile(
                name="google-oauth",
                source_type="google",
                mode="live",
                features=["drive", "gmail", "calendar", "sheets", "shared_token_store"],
            ),
            ConnectorProfile(
                name="github-oauth",
                source_type="github",
                mode="live",
                features=["oauth_login", "token_bootstrap", "issue_pr_future_sync"],
            ),
            ConnectorProfile(
                name="notion-oauth",
                source_type="notion",
                mode="live",
                features=["oauth_login", "token_bootstrap", "document_future_sync"],
            ),
            ConnectorProfile(
                name="jira-oauth",
                source_type="jira",
                mode="live",
                features=["oauth_login", "token_bootstrap", "issue_comment_future_sync"],
            ),
        ]

    def resolve(self, path: Path, profile: str | None = None) -> Connector:
        normalized = (profile or "").casefold().replace("_", "-")
        if normalized in {"markdown", "markdown-files"}:
            return MarkdownConnector()
        if normalized in {"slack", "slack-export"}:
            return SlackExportConnector()
        if normalized in {"jira", "jira-json"}:
            return JiraConnector()
        if normalized in {"github", "github-json"}:
            return GitHubConnector()
        if normalized in {"notion", "notion-json"}:
            return NotionConnector()
        if normalized in {"google-drive", "google-drive-json", "drive"}:
            return GoogleDriveConnector(pii_redaction=self._pii_redaction())
        if normalized in {"gmail", "gmail-json", "google-email", "google-mail"}:
            return GmailConnector(pii_redaction=self._pii_redaction())
        if normalized in {"google-calendar", "google-calendar-json", "calendar"}:
            return GoogleCalendarConnector(pii_redaction=self._pii_redaction())
        if normalized in {"google-sheets", "google-sheets-json", "sheets"}:
            return GoogleSheetsConnector(pii_redaction=self._pii_redaction())
        return ObsidianConnector()

    def runtime(self, path: Path, profile: str | None = None) -> ExportConnectorRuntime:
        normalized = (profile or "").casefold().replace("_", "-")
        selected_profile = self.profile(normalized or "obsidian")
        if selected_profile.mode == "live":
            raise ValueError(f"Live connector profile does not use path-based export runtime: {selected_profile.name}")
        return ExportConnectorRuntime(self.resolve(path, selected_profile.name), selected_profile)

    def profile(self, name: str) -> ConnectorProfile:
        normalized = name.casefold().replace("_", "-")
        aliases = {
            "slack": "slack-export",
            "jira": "jira-json",
            "github": "github-json",
            "markdown-files": "markdown",
            "drive": "google-drive-json",
            "google-drive": "google-drive-json",
            "gmail": "gmail-json",
            "google-email": "gmail-json",
            "google-mail": "gmail-json",
            "calendar": "google-calendar-json",
            "google-calendar": "google-calendar-json",
            "sheets": "google-sheets-json",
            "google-sheets": "google-sheets-json",
        }
        normalized = aliases.get(normalized, normalized)
        for profile in self.profiles():
            if profile.name == normalized:
                return profile
        raise ValueError(f"Unknown connector profile: {name}")

    def _pii_redaction(self) -> str:
        return load_config().security.pii_redaction
