"""Project official-news collection health without inventing market direction."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trading_ig_assistant.domain.context_sources import (
    NewsCollectionSnapshot,
    ProviderCollectionStatus,
)
from trading_ig_assistant.domain.macro_context import ContextSeverity, ContextSignal


def build_news_source_health_signal(
    snapshots: tuple[NewsCollectionSnapshot, ...],
    *,
    generated_at_utc: datetime,
    valid_for: timedelta,
) -> ContextSignal:
    """Return data-source health only; never a directional or event-risk score."""
    _require_utc(generated_at_utc)
    if valid_for <= timedelta(0):
        raise ValueError("news source-health validity must be positive")

    available = tuple(
        snapshot
        for snapshot in snapshots
        if snapshot.status is ProviderCollectionStatus.AVAILABLE
        and snapshot.collected_at_utc <= generated_at_utc < snapshot.collected_at_utc + valid_for
    )
    if snapshots and len(available) == len(snapshots):
        severity = ContextSeverity.GREEN
    elif available:
        severity = ContextSeverity.YELLOW
    else:
        severity = ContextSeverity.GRAY

    provider_count = len(snapshots)
    item_count = sum(len(snapshot.items) for snapshot in available)
    unavailable_ids = tuple(
        snapshot.provider_id
        for snapshot in snapshots
        if snapshot.status is ProviderCollectionStatus.UNAVAILABLE
    )
    stale_ids = tuple(
        snapshot.provider_id
        for snapshot in snapshots
        if snapshot.status is ProviderCollectionStatus.AVAILABLE
        and not snapshot.collected_at_utc
        <= generated_at_utc
        < snapshot.collected_at_utc + valid_for
    )
    summary = (
        f"Official sources available: {len(available)}/{provider_count}; "
        f"metadata items: {item_count}."
    )
    if unavailable_ids:
        summary += f" Unavailable: {', '.join(unavailable_ids)}."
    if stale_ids:
        summary += f" Stale or future collection: {', '.join(stale_ids)}."
    if not snapshots:
        summary = "No official news source is configured."

    return ContextSignal(
        signal_id="official-news-source-health",
        label="Official news sources",
        severity=severity,
        score=None,
        summary=summary,
        source="official-news-collection",
        source_url=None,
        observed_at_utc=generated_at_utc,
        valid_until_utc=(
            min(snapshot.collected_at_utc + valid_for for snapshot in available)
            if available
            else generated_at_utc + valid_for
        ),
        confidence=None,
        tags=("data_health", "official_news"),
    )


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("news source-health timestamp must use UTC")
