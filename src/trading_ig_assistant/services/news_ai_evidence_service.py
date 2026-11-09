"""Project normalized news metadata into non-directional evidence for AI context."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trading_ig_assistant.domain.ai_context import AI_EVIDENCE_TAG
from trading_ig_assistant.domain.context_sources import (
    NewsCollectionSnapshot,
    ProviderCollectionStatus,
    SourceUsageRights,
)
from trading_ig_assistant.domain.macro_context import ContextSeverity, ContextSignal


def build_news_ai_evidence_signals(
    snapshots: tuple[NewsCollectionSnapshot, ...],
    *,
    generated_at_utc: datetime,
    valid_for: timedelta,
    max_items: int = 20,
) -> tuple[ContextSignal, ...]:
    """Return bounded headline metadata as gray evidence without deterministic score or bias."""

    _require_utc(generated_at_utc)
    if valid_for <= timedelta(0):
        raise ValueError("AI news-evidence validity must be positive")
    if max_items <= 0:
        raise ValueError("AI news-evidence item limit must be positive")

    items = [
        (item, snapshot.collected_at_utc + valid_for)
        for snapshot in snapshots
        if snapshot.status is ProviderCollectionStatus.AVAILABLE
        and snapshot.collected_at_utc <= generated_at_utc < snapshot.collected_at_utc + valid_for
        for item in snapshot.items
        if item.usage_rights is not SourceUsageRights.UNKNOWN
    ]
    items.sort(key=lambda pair: (pair[0].published_at_utc, pair[0].item_id), reverse=True)
    return tuple(
        ContextSignal(
            signal_id=f"news:{item.item_id}",
            label=item.headline,
            severity=ContextSeverity.GRAY,
            score=None,
            summary=(
                f"Official metadata published at {item.published_at_utc.isoformat()}; "
                "no article body was collected."
            ),
            source=item.source,
            source_url=item.source_url,
            observed_at_utc=item.published_at_utc,
            valid_until_utc=valid_until_utc,
            confidence=None,
            tags=(AI_EVIDENCE_TAG, "official_news_metadata", item.category.value),
        )
        for item, valid_until_utc in items[:max_items]
    )


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("AI news-evidence generation must use UTC")
