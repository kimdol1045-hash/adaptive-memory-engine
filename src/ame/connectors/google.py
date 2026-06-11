from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ame.bronze.schema import BronzeDocument
from ame.connectors.base import SourceRef
from ame.connectors.json_helpers import first_present, read_json
from ame.security import PiiRedactionMode, redact_pii


class GoogleDriveConnector:
    source_type = "google_drive"
    profile_name = "google-drive-json"

    def __init__(self, pii_redaction: PiiRedactionMode = "off"):
        self.pii_redaction = pii_redaction

    def scan(self, path: Path) -> list[SourceRef]:
        refs: list[SourceRef] = []
        for file in _json_files(path):
            for index, row in enumerate(_rows(read_json(file), "files", "documents", "items")):
                if not isinstance(row, dict):
                    continue
                doc_id = _text(first_present(row, "id", "file_id", "document_id") or f"{file.stem}-{index}")
                title = _text(first_present(row, "name", "title") or doc_id)
                body = _text(first_present(row, "text", "body", "content", "description"))
                url = _text(first_present(row, "webViewLink", "web_url", "url", "alternateLink"))
                modified_at = _text(first_present(row, "modifiedTime", "modified_at", "updated_at"))
                folder = _text(first_present(row, "folder", "folder_path", "path", "parents"))
                owners = _people(first_present(row, "owners", "owner", "lastModifyingUser"))
                metadata = {
                    "title": title,
                    "connector": self.profile_name,
                    "google_service": "drive",
                    "document_id": doc_id,
                    "folder": folder,
                    "original_url": url,
                    "modified_at": modified_at,
                    "occurred_at": modified_at,
                    "owners": owners,
                    "memory_type": "Document",
                    "privacy_level": "private",
                }
                content = _frontmatter(
                    title,
                    {
                        "google_service": "drive",
                        "document_id": doc_id,
                        "folder": folder,
                        "modified_at": modified_at,
                        "occurred_at": modified_at,
                        "original_url": url,
                    },
                    ["# " + title, "", f"Folder: {folder}", "", body],
                )
                refs.append(
                    SourceRef(
                        path=file,
                        source_id=f"google_drive:{doc_id}",
                        content=_safe_content(content, self.pii_redaction),
                        metadata=_safe_metadata(metadata, self.pii_redaction),
                    )
                )
        return refs

    def load(self, corpus_id: str, ref: SourceRef) -> BronzeDocument:
        return _bronze(corpus_id, self.source_type, ref, self.profile_name)


class GmailConnector:
    source_type = "gmail"
    profile_name = "gmail-json"

    def __init__(self, pii_redaction: PiiRedactionMode = "off"):
        self.pii_redaction = pii_redaction

    def scan(self, path: Path) -> list[SourceRef]:
        refs: list[SourceRef] = []
        for file in _json_files(path):
            for index, row in enumerate(_rows(read_json(file), "threads", "messages", "items")):
                if not isinstance(row, dict):
                    continue
                messages = _messages(row)
                thread_id = _text(first_present(row, "threadId", "thread_id", "id") or f"{file.stem}-{index}")
                subject = _text(first_present(row, "subject", "title") or _first_message_value(messages, "subject") or thread_id)
                url = _text(first_present(row, "url", "web_url") or f"https://mail.google.com/mail/u/0/#all/{thread_id}")
                participants = sorted(set(_message_people(messages)))
                message_ids = _message_ids(messages)
                labels = _message_labels(row, messages)
                occurred_at = _text(
                    first_present(row, "date", "internalDate", "created_at", "updated_at")
                    or _first_message_value(messages, "date")
                    or _first_message_value(messages, "internalDate")
                )
                metadata = {
                    "title": subject,
                    "connector": self.profile_name,
                    "google_service": "gmail",
                    "thread_id": thread_id,
                    "message_ids": message_ids,
                    "labels": labels,
                    "original_url": url,
                    "occurred_at": occurred_at,
                    "participants": participants,
                    "memory_type": "Email",
                    "privacy_level": "private",
                }
                content_lines = ["# " + subject, "", f"Thread: {thread_id}", ""]
                for message in messages:
                    message_id = _text(first_present(message, "id", "message_id", "messageId"))
                    sender = _text(first_present(message, "from", "sender", "author"))
                    to = _text(first_present(message, "to", "recipients"))
                    cc = _text(first_present(message, "cc"))
                    date = _text(first_present(message, "date", "internalDate", "created_at"))
                    message_labels = ", ".join(_message_labels(message, []))
                    body = _text(first_present(message, "body", "text", "content", "snippet"))
                    content_lines.extend(
                        [
                            f"Message ID: {message_id}",
                            f"From: {sender}",
                            f"To: {to}",
                            f"Cc: {cc}",
                            f"Date: {date}",
                            f"Labels: {message_labels}",
                            "",
                            body,
                            "",
                        ]
                    )
                content = _frontmatter(
                    subject,
                    {
                        "google_service": "gmail",
                        "thread_id": thread_id,
                        "message_ids": ", ".join(message_ids),
                        "labels": ", ".join(labels),
                        "occurred_at": occurred_at,
                        "original_url": url,
                    },
                    content_lines,
                )
                refs.append(
                    SourceRef(
                        path=file,
                        source_id=f"gmail:{thread_id}",
                        content=_safe_content(content, self.pii_redaction),
                        metadata=_safe_metadata(metadata, self.pii_redaction),
                    )
                )
        return refs

    def load(self, corpus_id: str, ref: SourceRef) -> BronzeDocument:
        return _bronze(corpus_id, self.source_type, ref, self.profile_name)


class GoogleCalendarConnector:
    source_type = "google_calendar"
    profile_name = "google-calendar-json"

    def __init__(self, pii_redaction: PiiRedactionMode = "off"):
        self.pii_redaction = pii_redaction

    def scan(self, path: Path) -> list[SourceRef]:
        refs: list[SourceRef] = []
        for file in _json_files(path):
            for index, row in enumerate(_rows(read_json(file), "events", "items")):
                if not isinstance(row, dict):
                    continue
                event_id = _text(first_present(row, "id", "event_id", "iCalUID") or f"{file.stem}-{index}")
                calendar_id = _text(first_present(row, "calendar_id", "calendarId") or "primary")
                title = _text(first_present(row, "summary", "title", "name") or event_id)
                start = _date_value(first_present(row, "start", "start_time", "starts_at"))
                end = _date_value(first_present(row, "end", "end_time", "ends_at"))
                attendees = _people(first_present(row, "attendees", "participants"))
                url = _text(first_present(row, "htmlLink", "url", "web_url"))
                location = _text(first_present(row, "location", "meeting_location"))
                description = _text(first_present(row, "description", "body", "content"))
                metadata = {
                    "title": title,
                    "connector": self.profile_name,
                    "google_service": "calendar",
                    "calendar_id": calendar_id,
                    "event_id": event_id,
                    "original_url": url,
                    "start": start,
                    "end": end,
                    "location": location,
                    "occurred_at": start,
                    "participants": attendees,
                    "memory_type": "Meeting",
                    "privacy_level": "private",
                }
                content = _frontmatter(
                    title,
                    {
                        "google_service": "calendar",
                        "calendar_id": calendar_id,
                        "event_id": event_id,
                        "start": start,
                        "end": end,
                        "location": location,
                        "occurred_at": start,
                        "original_url": url,
                    },
                    [
                        "# " + title,
                        "",
                        f"Start: {start}",
                        f"End: {end}",
                        f"Location: {location}",
                        f"Participants: {', '.join(attendees)}",
                        "",
                        description,
                    ],
                )
                refs.append(
                    SourceRef(
                        path=file,
                        source_id=f"google_calendar:{calendar_id}:{event_id}",
                        content=_safe_content(content, self.pii_redaction),
                        metadata=_safe_metadata(metadata, self.pii_redaction),
                    )
                )
        return refs

    def load(self, corpus_id: str, ref: SourceRef) -> BronzeDocument:
        return _bronze(corpus_id, self.source_type, ref, self.profile_name)


class GoogleSheetsConnector:
    source_type = "google_sheets"
    profile_name = "google-sheets-json"

    def __init__(self, pii_redaction: PiiRedactionMode = "off"):
        self.pii_redaction = pii_redaction

    def scan(self, path: Path) -> list[SourceRef]:
        refs: list[SourceRef] = []
        for file in _json_files(path):
            data = read_json(file)
            parent = data if isinstance(data, dict) else {}
            for index, row in enumerate(_sheet_rows(data)):
                spreadsheet_id = _text(
                    first_present(row, "spreadsheet_id", "spreadsheetId")
                    or first_present(parent, "spreadsheet_id", "spreadsheetId", "id")
                    or file.stem
                )
                sheet_name = _text(first_present(row, "sheet_name", "sheetName") or first_present(parent, "sheet_name", "sheetName") or "Sheet1")
                row_index = _text(first_present(row, "row_index", "rowIndex") or index + 1)
                title = _text(first_present(row, "title", "summary") or f"{sheet_name} row {row_index}")
                values = _sheet_values(row)
                url = _text(first_present(row, "url", "web_url") or first_present(parent, "url", "web_url"))
                modified_at = _text(first_present(row, "modified_at", "updated_at") or first_present(parent, "modified_at", "updated_at"))
                occurred_at = modified_at
                metadata = {
                    "title": title,
                    "connector": self.profile_name,
                    "google_service": "sheets",
                    "spreadsheet_id": spreadsheet_id,
                    "sheet_name": sheet_name,
                    "row_index": row_index,
                    "original_url": url,
                    "modified_at": modified_at,
                    "occurred_at": occurred_at,
                    "memory_type": "Document",
                    "privacy_level": "private",
                }
                content = _frontmatter(
                    title,
                    {
                        "google_service": "sheets",
                        "spreadsheet_id": spreadsheet_id,
                        "sheet_name": sheet_name,
                        "row_index": row_index,
                        "occurred_at": occurred_at,
                        "original_url": url,
                    },
                    ["# " + title, "", values],
                )
                refs.append(
                    SourceRef(
                        path=file,
                        source_id=f"google_sheets:{spreadsheet_id}:{sheet_name}:{row_index}",
                        content=_safe_content(content, self.pii_redaction),
                        metadata=_safe_metadata(metadata, self.pii_redaction),
                    )
                )
        return refs

    def load(self, corpus_id: str, ref: SourceRef) -> BronzeDocument:
        return _bronze(corpus_id, self.source_type, ref, self.profile_name)


def _json_files(path: Path) -> list[Path]:
    root = path.expanduser().resolve()
    return [root] if root.is_file() else sorted(root.rglob("*.json"))


def _rows(data: Any, *keys: str) -> list[Any]:
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in keys:
        rows = data.get(key)
        if isinstance(rows, list):
            return rows
    return [data]


def _messages(row: dict[str, Any]) -> list[dict[str, Any]]:
    messages = row.get("messages")
    if isinstance(messages, list):
        return [message for message in messages if isinstance(message, dict)]
    return [row]


def _first_message_value(messages: list[dict[str, Any]], key: str) -> Any:
    for message in messages:
        value = message.get(key)
        if value:
            return value
    return None


def _message_people(messages: list[dict[str, Any]]) -> list[str]:
    people: list[str] = []
    for message in messages:
        for key in ["from", "sender", "author", "to", "cc", "bcc", "recipients"]:
            people.extend(_people(message.get(key)))
    return people


def _message_ids(messages: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for message in messages:
        message_id = _text(first_present(message, "id", "message_id", "messageId"))
        if message_id:
            ids.append(message_id)
    return _unique(ids)


def _message_labels(row: dict[str, Any], messages: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    for key in ["labelIds", "label_ids", "labels"]:
        labels.extend(_people(row.get(key)))
    for message in messages:
        for key in ["labelIds", "label_ids", "labels"]:
            labels.extend(_people(message.get(key)))
    return _unique(labels)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique_values.append(value)
    return unique_values


def _sheet_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [_sheet_row(row, index) for index, row in enumerate(data)]
    if not isinstance(data, dict):
        return []
    rows = data.get("rows")
    if isinstance(rows, list):
        return [_sheet_row(row, index) for index, row in enumerate(rows)]
    values = data.get("values")
    if isinstance(values, list):
        return [_sheet_row(row, index) for index, row in enumerate(values)]
    return [_sheet_row(data, 0)]


def _sheet_row(row: Any, index: int) -> dict[str, Any]:
    if isinstance(row, dict):
        row.setdefault("row_index", index + 1)
        return row
    return {"row_index": index + 1, "values": row}


def _sheet_values(row: dict[str, Any]) -> str:
    values = first_present(row, "values", "cells", "data")
    if isinstance(values, dict):
        return "\n".join(f"{key}: {_text(value)}" for key, value in values.items())
    if isinstance(values, list):
        return "\n".join(f"- {_text(value)}" for value in values)
    return _text(first_present(row, "body", "content", "text", "description") or row)


def _frontmatter(title: str, values: dict[str, str], body_lines: list[str]) -> str:
    frontmatter = ["---", f"title: {title}"]
    for key, value in values.items():
        frontmatter.append(f"{key}: {value}")
    frontmatter.extend(["---", ""])
    return "\n".join(frontmatter + body_lines + [""])


def _bronze(corpus_id: str, source_type: str, ref: SourceRef, connector: str) -> BronzeDocument:
    content = ref.content or ref.path.read_text(encoding="utf-8")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    metadata = {"path": str(ref.path), "connector": connector}
    metadata.update(ref.metadata)
    return BronzeDocument(
        id=f"bronze_{digest[:16]}",
        corpus_id=corpus_id,
        source_type=source_type,
        source_id=ref.source_id,
        content=content,
        metadata=metadata,
        content_hash=f"sha256:{digest}",
    )


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ["displayName", "emailAddress", "email", "name", "dateTime", "date", "value"]:
            if value.get(key) is not None:
                return _text(value[key])
        return " ".join(f"{key}={_text(item)}" for key, item in value.items())
    if isinstance(value, list):
        return ", ".join(_text(item) for item in value if _text(item))
    return str(value)


def _date_value(value: Any) -> str:
    if isinstance(value, dict):
        return _text(first_present(value, "dateTime", "date"))
    return _text(value)


def _people(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        people: list[str] = []
        for item in value:
            people.extend(_people(item))
        return people
    if isinstance(value, dict):
        if "emailAddress" in value and isinstance(value["emailAddress"], dict):
            return _people(value["emailAddress"])
        text = _text(first_present(value, "email", "address", "displayName", "name"))
        return [text] if text else []
    text = _text(value)
    return [part.strip() for part in text.replace(";", ",").split(",") if part.strip()]


def _safe_metadata(metadata: dict[str, Any], mode: PiiRedactionMode) -> dict[str, Any]:
    payload = dict(metadata)
    payload["pii_redaction"] = mode
    if mode in {"metadata", "content"}:
        return redact_pii(payload)
    return payload


def _safe_content(content: str, mode: PiiRedactionMode) -> str:
    return redact_pii(content) if mode == "content" else content
