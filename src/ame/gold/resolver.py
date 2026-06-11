from __future__ import annotations

from collections import defaultdict

from ame.gold.schema import GoldEdge, GoldTimelineEvent


class SupersedesResolver:
    """Resolve currentness from SUPERSEDES edges.

    Rule: if A SUPERSEDES B, B is no longer current and A remains eligible to be
    current. Current decisions are accepted decisions that are not superseded.
    """

    def resolve(self, timeline: list[GoldTimelineEvent], edges: list[GoldEdge]) -> list[GoldTimelineEvent]:
        timeline = self._merge_events(timeline)
        by_title = {self._key(event.title): event for event in timeline}
        supersedes_by_source: dict[str, set[str]] = defaultdict(set)
        superseded_by_target: dict[str, set[str]] = defaultdict(set)

        for edge in edges:
            if edge.relation != "SUPERSEDES":
                continue
            source_key = self._key(edge.source)
            target_key = self._key(edge.target)
            supersedes_by_source[source_key].add(edge.target)
            superseded_by_target[target_key].add(edge.source)

        resolved: list[GoldTimelineEvent] = []
        for index, event in enumerate(timeline):
            event_key = self._key(event.title)
            supersedes = sorted(set(event.supersedes) | supersedes_by_source.get(event_key, set()))
            superseded_by = sorted(set(event.superseded_by) | superseded_by_target.get(event_key, set()))
            valid_to = event.valid_to or self._first_valid_from(superseded_by, by_title)
            resolved_event = event.model_copy(
                update={
                    "supersedes": supersedes,
                    "superseded_by": superseded_by,
                    "valid_to": valid_to,
                    "current": event.status == "accepted" and not superseded_by,
                }
            )
            resolved.append(resolved_event)

        return sorted(resolved, key=lambda event: (event.valid_from or "9999-99-99", self._original_index(event, timeline)))

    def _merge_events(self, timeline: list[GoldTimelineEvent]) -> list[GoldTimelineEvent]:
        merged_by_key: dict[str, GoldTimelineEvent] = {}
        status_rank = {"accepted": 4, "proposed": 3, "rejected": 2, "superseded": 1, None: 0}
        for event in timeline:
            key = self._key(event.title)
            existing = merged_by_key.get(key)
            if existing is None:
                merged_by_key[key] = event
                continue
            status = existing.status
            if status_rank.get(event.status, 0) > status_rank.get(existing.status, 0):
                status = event.status
            dates = [date for date in [existing.valid_from, event.valid_from] if date]
            merged_by_key[key] = existing.model_copy(
                update={
                    "status": status,
                    "project": existing.project or event.project,
                    "rationale": existing.rationale or event.rationale,
                    "valid_from": sorted(dates)[0] if dates else None,
                    "valid_to": existing.valid_to or event.valid_to,
                    "supersedes": sorted(set(existing.supersedes + event.supersedes)),
                    "superseded_by": sorted(set(existing.superseded_by + event.superseded_by)),
                    "participants": sorted(set(existing.participants + event.participants)),
                    "source_ids": sorted(set(existing.source_ids + event.source_ids)),
                    "confidence": max(existing.confidence or 0.0, event.confidence or 0.0) or None,
                }
            )
        return list(merged_by_key.values())

    def _first_valid_from(self, superseding_titles: list[str], by_title: dict[str, GoldTimelineEvent]) -> str | None:
        dates = [
            event.valid_from
            for title in superseding_titles
            if (event := by_title.get(self._key(title))) is not None and event.valid_from
        ]
        return sorted(dates)[0] if dates else None

    def _original_index(self, event: GoldTimelineEvent, timeline: list[GoldTimelineEvent]) -> int:
        for index, original in enumerate(timeline):
            if original.id == event.id:
                return index
        return len(timeline)

    def _key(self, title: str) -> str:
        return " ".join(title.casefold().split())
