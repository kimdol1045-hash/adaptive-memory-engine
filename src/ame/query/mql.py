from __future__ import annotations

import re

from pydantic import BaseModel, Field

from ame.gold.schema import GoldTimelineEvent
from ame.query.diff import MemoryDiffEngine
from ame.silver.schema import SilverRationale


class MqlResult(BaseModel):
    answer: str
    matched_titles: list[str] = Field(default_factory=list)
    operation: str


class MqlEngine:
    def execute(
        self,
        query: str,
        timeline: list[GoldTimelineEvent],
        rationales: list[SilverRationale] | None = None,
    ) -> MqlResult | None:
        normalized = " ".join(query.strip().split())
        lowered = normalized.casefold()
        if lowered == "find decisions where current=true":
            current = [event for event in timeline if event.current and event.status == "accepted"]
            titles = ", ".join(event.title for event in current) or "없음"
            return MqlResult(
                operation="find_current_decisions",
                matched_titles=[event.title for event in current],
                answer=f"FIND decisions WHERE current=true 결과: accepted decision 중 current=true인 decision은 {titles}이다.",
            )
        if match := re.match(r'why\s+decision=["\']?([^"\']+)["\']?$', normalized, flags=re.IGNORECASE):
            needle = match.group(1).casefold()
            events = [event for event in timeline if needle in event.title.casefold()]
            rationale_items = [
                rationale
                for rationale in rationales or []
                if needle in rationale.decision_title.casefold() or rationale.decision_title.casefold() in needle
            ]
            if rationale_items:
                rationale = "; ".join(f"{item.rationale_text} ({item.category})" for item in rationale_items)
            else:
                rationale = events[0].rationale if events and events[0].rationale else "rationale 근거 없음"
            return MqlResult(
                operation="why_decision",
                matched_titles=[event.title for event in events] or sorted({item.decision_title for item in rationale_items}),
                answer=(
                    f'WHY decision="{match.group(1)}" 결과: '
                    f"matched decision={', '.join([event.title for event in events] or sorted({item.decision_title for item in rationale_items}) or [match.group(1)])}; "
                    f"decision={match.group(1)}에 연결된 rationale memory는 {rationale}"
                ),
            )
        if lowered.startswith("show timeline"):
            project = self._project_filter(normalized)
            events = [event for event in timeline if not project or (event.project and project.casefold() in event.project.casefold())]
            if not events:
                events = timeline
            summary = " → ".join(event.title for event in events)
            suffix = f' FOR project="{project}"' if project else ""
            return MqlResult(
                operation="show_timeline",
                matched_titles=[event.title for event in events],
                answer=f"SHOW timeline{suffix} 결과: {summary}",
            )
        if lowered.startswith("show changes"):
            diff = MemoryDiffEngine().diff_last_days(timeline, days=7)
            changed = diff.accepted_decisions + diff.superseded_decisions + diff.current_false_decisions
            return MqlResult(
                operation="show_changes",
                matched_titles=changed,
                answer=(
                    "SHOW CHANGES LAST 7 DAYS 결과: "
                    f"accepted decision={diff.accepted_decisions}, SUPERSEDES={diff.superseded_decisions}, "
                    f"current=false={diff.current_false_decisions}"
                ),
            )
        return None

    def _project_filter(self, query: str) -> str | None:
        match = re.search(r'for\s+project=["\']?([^"\']+)["\']?$', query, flags=re.IGNORECASE)
        return match.group(1).strip() if match else None
