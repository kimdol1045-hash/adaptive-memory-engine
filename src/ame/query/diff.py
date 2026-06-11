from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel, Field

from ame.gold.schema import GoldTimelineEvent


class MemoryDiff(BaseModel):
    window_days: int
    since: str | None = None
    accepted_decisions: list[str] = Field(default_factory=list)
    superseded_decisions: list[str] = Field(default_factory=list)
    current_false_decisions: list[str] = Field(default_factory=list)


class MemoryDiffEngine:
    def diff_last_days(self, timeline: list[GoldTimelineEvent], days: int = 7) -> MemoryDiff:
        dated = [(event, self._parse_date(event.valid_from)) for event in timeline if event.valid_from]
        if not dated:
            return MemoryDiff(window_days=days)
        newest = max(day for _, day in dated if day is not None)
        since = newest - timedelta(days=days)
        in_window = [event for event, day in dated if day is not None and day >= since]
        return MemoryDiff(
            window_days=days,
            since=since.isoformat(),
            accepted_decisions=[event.title for event in in_window if event.status == "accepted"],
            superseded_decisions=[event.title for event in in_window if event.supersedes],
            current_false_decisions=[event.title for event in timeline if event.current is False and event.superseded_by],
        )

    def _parse_date(self, value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
