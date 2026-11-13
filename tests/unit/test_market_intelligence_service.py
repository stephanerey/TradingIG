from datetime import UTC, datetime, timedelta

from trading_ig_assistant.domain.context_sources import (
    ContextCategory,
    ContextImportance,
    NewsCollectionSnapshot,
    NewsItem,
    ProviderCollectionStatus,
    SourceUsageRights,
)
from trading_ig_assistant.domain.market_intelligence import (
    IntelligenceCoverageStatus,
    IntelligenceNewsRecord,
    IntelligenceProviderKind,
    IntelligenceProviderResult,
    PublicationTimeStatus,
    VerificationStatus,
)
from trading_ig_assistant.services.market_intelligence_service import (
    build_market_intelligence_snapshot,
    canonicalize_source_url,
    normalize_headline,
)

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)


def _news(item_id, source, url, *, headline="Oil supply disruption announced"):
    return NewsItem(
        schema_version=1,
        item_id=item_id,
        headline=headline,
        summary=None,
        category=ContextCategory.ENERGY,
        importance=ContextImportance.UNKNOWN,
        published_at_utc=NOW - timedelta(minutes=20),
        observed_at_utc=NOW,
        source=source,
        source_url=url,
        usage_rights=SourceUsageRights.METADATA_ONLY,
        tags=(source,),
    )


def test_deduplication_strips_tracking_and_marks_distinct_sources_corroborated() -> None:
    tavily_record = IntelligenceNewsRecord(
        _news("t-1", "source-a.example", "https://source-a.example/story?utm_source=x"),
        "tavily-news",
        IntelligenceProviderKind.TAVILY,
        PublicationTimeStatus.PROVIDER_ESTIMATE,
        VerificationStatus.SINGLE_SOURCE,
    )
    gdelt_record = IntelligenceNewsRecord(
        _news("g-1", "source-b.example", "https://source-a.example/story?fbclid=y"),
        "gdelt-doc",
        IntelligenceProviderKind.GDELT,
        PublicationTimeStatus.PROVIDER_ESTIMATE,
        VerificationStatus.UNCONFIRMED,
    )
    results = (
        IntelligenceProviderResult(
            "tavily-news",
            IntelligenceProviderKind.TAVILY,
            "oil",
            (tavily_record,),
            NOW,
        ),
        IntelligenceProviderResult(
            "gdelt-doc",
            IntelligenceProviderKind.GDELT,
            "oil",
            (gdelt_record,),
            NOW,
        ),
    )

    snapshot = build_market_intelligence_snapshot(
        provider_results=results,
        official_snapshots=(),
        generated_at_utc=NOW,
    )

    assert snapshot.coverage_status is IntelligenceCoverageStatus.FRESH
    assert len(snapshot.events) == 1
    event = snapshot.events[0]
    assert event.verification_status is VerificationStatus.CORROBORATED
    assert event.source_names == ("source-a.example", "source-b.example")
    assert len(event.source_record_ids) == 2


def test_official_sources_are_composed_and_unavailable_sources_degrade_coverage() -> None:
    official = NewsCollectionSnapshot(
        1,
        "federal-reserve-rss",
        ProviderCollectionStatus.AVAILABLE,
        (_news("fed-1", "Federal Reserve", "https://federalreserve.gov/release"),),
        NOW,
        (),
    )
    unavailable = NewsCollectionSnapshot(
        1,
        "ecb-rss",
        ProviderCollectionStatus.UNAVAILABLE,
        (),
        NOW,
        ("NEWS_PROVIDER_ERROR",),
    )

    snapshot = build_market_intelligence_snapshot(
        provider_results=(),
        official_snapshots=(official, unavailable),
        generated_at_utc=NOW,
    )

    assert snapshot.coverage_status is IntelligenceCoverageStatus.DEGRADED
    assert snapshot.events[0].verification_status is VerificationStatus.OFFICIAL
    assert snapshot.reason_codes == ("ecb-rss:NEWS_PROVIDER_ERROR",)


def test_stale_and_empty_coverage_are_explicit() -> None:
    old_news = _news("old", "archive.example", "https://archive.example/old")
    old_news = NewsItem(
        **{
            **old_news.__dict__,
            "published_at_utc": NOW - timedelta(hours=9),
            "observed_at_utc": NOW - timedelta(hours=8),
        }
    )
    record = IntelligenceNewsRecord(
        old_news,
        "tavily-news",
        IntelligenceProviderKind.TAVILY,
        PublicationTimeStatus.PROVIDER_ESTIMATE,
        VerificationStatus.SINGLE_SOURCE,
    )
    result = IntelligenceProviderResult(
        "tavily-news",
        IntelligenceProviderKind.TAVILY,
        "old",
        (record,),
        NOW,
    )
    stale = build_market_intelligence_snapshot(
        provider_results=(result,),
        official_snapshots=(),
        generated_at_utc=NOW,
        stale_after=timedelta(hours=6),
    )
    assert stale.coverage_status is IntelligenceCoverageStatus.STALE
    assert "MARKET_INTELLIGENCE_STALE" in stale.reason_codes

    empty = build_market_intelligence_snapshot(
        provider_results=(),
        official_snapshots=(),
        generated_at_utc=NOW,
    )
    assert empty.coverage_status is IntelligenceCoverageStatus.UNAVAILABLE
    assert empty.reason_codes == ("MARKET_INTELLIGENCE_EMPTY",)


def test_canonicalization_and_headline_normalization_are_deterministic() -> None:
    assert canonicalize_source_url(
        "https://EXAMPLE.com/story/?utm_campaign=x&b=2&a=1#section"
    ) == "https://example.com/story?a=1&b=2"
    assert normalize_headline("  BCE : hausse des taux ! ") == "bce hausse des taux"
