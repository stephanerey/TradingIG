"""Collect normalized news while degrading provider failures explicitly."""

from __future__ import annotations

from datetime import UTC, datetime

from trading_ig_assistant.adapters.news_provider import NewsProvider
from trading_ig_assistant.domain.context_sources import (
    NewsCollectionSnapshot,
    NewsItem,
    ProviderCollectionStatus,
)


def collect_news(
    provider: NewsProvider,
    *,
    as_of_utc: datetime,
) -> NewsCollectionSnapshot:
    _require_utc(as_of_utc)
    try:
        provider_id = provider.provider_id
    except Exception:
        return _unavailable("invalid-news-provider", as_of_utc, "NEWS_PROVIDER_ERROR")
    if not isinstance(provider_id, str) or not provider_id.strip():
        return _unavailable("invalid-news-provider", as_of_utc, "NEWS_PROVIDER_INVALID")
    try:
        items = tuple(provider.fetch_news(as_of_utc=as_of_utc))
        if any(not isinstance(item, NewsItem) for item in items):
            raise TypeError("provider returned a non-news record")
        return NewsCollectionSnapshot(
            schema_version=1,
            provider_id=provider_id,
            status=ProviderCollectionStatus.AVAILABLE,
            items=items,
            collected_at_utc=as_of_utc,
            reason_codes=(),
        )
    except Exception:
        return _unavailable(provider_id, as_of_utc, "NEWS_PROVIDER_ERROR")


def _unavailable(
    provider_id: str,
    collected_at_utc: datetime,
    reason_code: str,
) -> NewsCollectionSnapshot:
    return NewsCollectionSnapshot(
        schema_version=1,
        provider_id=provider_id,
        status=ProviderCollectionStatus.UNAVAILABLE,
        items=(),
        collected_at_utc=collected_at_utc,
        reason_codes=(reason_code,),
    )


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("news collection timestamp must use UTC")
