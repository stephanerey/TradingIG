"""Normalize, compose and deduplicate provider-neutral intelligence metadata."""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from trading_ig_assistant.domain.context_sources import (
    NewsCollectionSnapshot,
    ProviderCollectionStatus,
)
from trading_ig_assistant.domain.market_intelligence import (
    IntelligenceCoverageStatus,
    IntelligenceNewsRecord,
    IntelligenceProviderKind,
    IntelligenceProviderResult,
    MarketIntelligenceEvent,
    MarketIntelligenceSnapshot,
    PublicationTimeStatus,
    VerificationStatus,
)

_TRACKING_QUERY_PREFIXES = ("utm_",)
_TRACKING_QUERY_NAMES = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def build_market_intelligence_snapshot(
    *,
    provider_results: tuple[IntelligenceProviderResult, ...],
    official_snapshots: tuple[NewsCollectionSnapshot, ...],
    generated_at_utc: datetime,
    stale_after: timedelta = timedelta(hours=6),
    reason_codes: tuple[str, ...] = (),
) -> MarketIntelligenceSnapshot:
    _require_utc(generated_at_utc)
    if stale_after <= timedelta(0):
        raise ValueError("market intelligence freshness window must be positive")
    records = [record for result in provider_results for record in result.records]
    for snapshot in official_snapshots:
        if snapshot.status is ProviderCollectionStatus.UNAVAILABLE:
            reason_codes += tuple(
                f"{snapshot.provider_id}:{code}" for code in snapshot.reason_codes
            )
            continue
        records.extend(_official_records(snapshot))
    events = _deduplicate(tuple(records))
    provider_ids = tuple(
        sorted(
            {
                *(result.provider_id for result in provider_results),
                *(snapshot.provider_id for snapshot in official_snapshots),
            }
        )
    )
    normalized_reasons = tuple(dict.fromkeys(reason_codes))
    if not events:
        status = IntelligenceCoverageStatus.UNAVAILABLE
        if not normalized_reasons:
            normalized_reasons = ("MARKET_INTELLIGENCE_EMPTY",)
    elif generated_at_utc - max(event.observed_at_utc for event in events) > stale_after:
        status = IntelligenceCoverageStatus.STALE
        normalized_reasons = tuple(
            dict.fromkeys((*normalized_reasons, "MARKET_INTELLIGENCE_STALE"))
        )
    elif normalized_reasons:
        status = IntelligenceCoverageStatus.DEGRADED
    else:
        status = IntelligenceCoverageStatus.FRESH
    return MarketIntelligenceSnapshot(
        generated_at_utc=generated_at_utc,
        coverage_status=status,
        events=events,
        provider_ids=provider_ids,
        reason_codes=normalized_reasons,
    )


def canonicalize_source_url(value: str) -> str:
    parts = urlsplit(value.strip())
    query = urlencode(
        sorted(
            (name, item)
            for name, item in parse_qsl(parts.query, keep_blank_values=False)
            if name.casefold() not in _TRACKING_QUERY_NAMES
            and not name.casefold().startswith(_TRACKING_QUERY_PREFIXES)
        )
    )
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(
        (
            parts.scheme.casefold(),
            parts.netloc.casefold(),
            path,
            query,
            "",
        )
    )


def normalize_headline(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", without_marks))


def _official_records(snapshot: NewsCollectionSnapshot) -> tuple[IntelligenceNewsRecord, ...]:
    return tuple(
        IntelligenceNewsRecord(
            news=item,
            provider_id=snapshot.provider_id,
            provider_kind=IntelligenceProviderKind.OFFICIAL,
            publication_time_status=PublicationTimeStatus.REPORTED,
            verification_status=VerificationStatus.OFFICIAL,
        )
        for item in snapshot.items
    )


def _deduplicate(
    records: tuple[IntelligenceNewsRecord, ...],
) -> tuple[MarketIntelligenceEvent, ...]:
    groups: list[list[IntelligenceNewsRecord]] = []
    key_to_group: dict[str, int] = {}
    for record in sorted(records, key=lambda item: item.news.item_id):
        keys = _record_keys(record)
        matching = sorted({key_to_group[key] for key in keys if key in key_to_group})
        if matching:
            target = matching[0]
            groups[target].append(record)
            for source in reversed(matching[1:]):
                groups[target].extend(groups[source])
                groups[source] = []
                for known_key, group_index in tuple(key_to_group.items()):
                    if group_index == source:
                        key_to_group[known_key] = target
        else:
            target = len(groups)
            groups.append([record])
        for key in keys:
            key_to_group[key] = target
    events = tuple(_event_from_group(tuple(group)) for group in groups if group)
    return tuple(
        sorted(events, key=lambda item: (item.published_at_utc, item.event_id), reverse=True)
    )


def _record_keys(record: IntelligenceNewsRecord) -> tuple[str, ...]:
    keys = [f"title:{normalize_headline(record.news.headline)}"]
    if record.news.source_url:
        keys.append(f"url:{canonicalize_source_url(record.news.source_url)}")
    return tuple(keys)


def _event_from_group(
    group: tuple[IntelligenceNewsRecord, ...],
) -> MarketIntelligenceEvent:
    ordered = sorted(
        group,
        key=lambda item: (
            item.provider_kind is IntelligenceProviderKind.OFFICIAL,
            item.relevance_score or 0,
            item.news.published_at_utc,
            item.news.item_id,
        ),
        reverse=True,
    )
    primary = ordered[0]
    source_names = tuple(dict.fromkeys(item.news.source for item in ordered))
    source_urls = tuple(
        dict.fromkeys(item.news.source_url for item in ordered if item.news.source_url)
    )
    provider_ids = tuple(dict.fromkeys(item.provider_id for item in ordered))
    source_ids = tuple(dict.fromkeys(item.news.item_id for item in ordered))
    if any(item.provider_kind is IntelligenceProviderKind.OFFICIAL for item in ordered):
        verification = VerificationStatus.OFFICIAL
    elif len({item.news.source.casefold() for item in ordered}) >= 2:
        verification = VerificationStatus.CORROBORATED
    elif all(item.provider_kind is IntelligenceProviderKind.GDELT for item in ordered):
        verification = VerificationStatus.UNCONFIRMED
    else:
        verification = VerificationStatus.SINGLE_SOURCE
    publication_status = _publication_status(ordered)
    published_at = min(item.news.published_at_utc for item in ordered)
    identity = "\0".join(sorted(source_ids))
    return MarketIntelligenceEvent(
        event_id=sha256(f"market-intelligence\0{identity}".encode()).hexdigest(),
        headline=primary.news.headline,
        category=primary.news.category,
        importance=primary.news.importance,
        published_at_utc=published_at,
        observed_at_utc=max(item.news.observed_at_utc for item in ordered),
        publication_time_status=publication_status,
        verification_status=verification,
        source_names=source_names,
        source_urls=source_urls,
        provider_ids=provider_ids,
        source_record_ids=source_ids,
        tags=tuple(dict.fromkeys(tag for item in ordered for tag in item.news.tags)),
    )


def _publication_status(
    records: list[IntelligenceNewsRecord],
) -> PublicationTimeStatus:
    statuses = {record.publication_time_status for record in records}
    if PublicationTimeStatus.REPORTED in statuses:
        return PublicationTimeStatus.REPORTED
    if PublicationTimeStatus.PROVIDER_ESTIMATE in statuses:
        return PublicationTimeStatus.PROVIDER_ESTIMATE
    return PublicationTimeStatus.UNKNOWN


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("market intelligence timestamp must use UTC")
