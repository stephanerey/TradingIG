from datetime import UTC, datetime, timedelta

from trading_ig_assistant.domain.ai_context import AIAnalysisStatus
from trading_ig_assistant.domain.context_sources import (
    ContextCategory,
    ContextImportance,
    NewsCollectionSnapshot,
    NewsItem,
    ProviderCollectionStatus,
    SourceUsageRights,
)
from trading_ig_assistant.domain.macro_context import (
    ContextSeverity,
    DirectionalBias,
    EventRisk,
)
from trading_ig_assistant.domain.market_intelligence import (
    IntelligenceNewsRecord,
    IntelligenceProviderKind,
    PublicationTimeStatus,
    VerificationStatus,
)
from trading_ig_assistant.services.ai_context_service import build_market_context_snapshot
from trading_ig_assistant.services.macro_context_service import MacroContextService
from trading_ig_assistant.services.market_intelligence_scheduler import (
    IntelligenceFreshnessPolicy,
)
from trading_ig_assistant.services.news_ai_evidence_service import (
    build_news_ai_evidence_signals,
    select_ai_article_candidates,
)

NOW = datetime(2026, 11, 4, 16, 0, tzinfo=UTC)


def _news_item(item_id: str, minutes_ago: int) -> NewsItem:
    return NewsItem(
        schema_version=1,
        item_id=item_id,
        headline=f"Official headline {item_id}",
        summary=None,
        category=ContextCategory.CENTRAL_BANK,
        importance=ContextImportance.UNKNOWN,
        published_at_utc=NOW - timedelta(minutes=minutes_ago),
        observed_at_utc=NOW,
        source="Official source",
        source_url=f"https://official.example/{item_id}",
        usage_rights=SourceUsageRights.METADATA_ONLY,
        tags=("official",),
    )


def _record(
    item_id: str,
    *,
    category: ContextCategory = ContextCategory.OTHER,
    source: str = "source.example",
    hours_ago: int = 1,
    relevance: float = 0.8,
    url_suffix: str | None = None,
) -> IntelligenceNewsRecord:
    item = NewsItem(
        schema_version=1,
        item_id=item_id,
        headline=f"Headline {item_id}",
        summary=None,
        category=category,
        importance=ContextImportance.UNKNOWN,
        published_at_utc=NOW - timedelta(hours=hours_ago),
        observed_at_utc=NOW,
        source=source,
        source_url=f"https://{source}/{url_suffix or item_id}",
        usage_rights=SourceUsageRights.METADATA_ONLY,
        tags=("tavily-news",),
    )
    return IntelligenceNewsRecord(
        news=item,
        provider_id="tavily-news",
        provider_kind=IntelligenceProviderKind.TAVILY,
        publication_time_status=PublicationTimeStatus.PROVIDER_ESTIMATE,
        verification_status=VerificationStatus.SINGLE_SOURCE,
        relevance_score=relevance,
        search_excerpt=f"Evidence for {item_id}. " * 30,
    )


def test_news_metadata_becomes_bounded_gray_ai_evidence_without_macro_bias() -> None:
    snapshot = NewsCollectionSnapshot(
        schema_version=1,
        provider_id="official-provider",
        status=ProviderCollectionStatus.AVAILABLE,
        items=(_news_item("older", 10), _news_item("newer", 1)),
        collected_at_utc=NOW,
        reason_codes=(),
    )

    signals = build_news_ai_evidence_signals(
        (snapshot,),
        generated_at_utc=NOW,
        valid_for=timedelta(minutes=15),
        max_items=1,
    )
    state = MacroContextService().build_state(signals, NOW)

    assert len(signals) == 1
    assert signals[0].signal_id == "news:newer"
    assert signals[0].severity is ContextSeverity.GRAY
    assert signals[0].score is None
    assert signals[0].confidence is None
    assert signals[0].tags == (
        "ai_evidence",
        "official_news_metadata",
        "central_bank",
    )
    assert state.index_bias is DirectionalBias.UNKNOWN
    assert state.event_risk is EventRisk.UNKNOWN


def test_gray_ai_evidence_can_be_cited_without_becoming_deterministic_context() -> None:
    collection = NewsCollectionSnapshot(
        schema_version=1,
        provider_id="official-provider",
        status=ProviderCollectionStatus.AVAILABLE,
        items=(_news_item("evidence", 1),),
        collected_at_utc=NOW,
        reason_codes=(),
    )
    evidence = build_news_ai_evidence_signals(
        (collection,),
        generated_at_utc=NOW,
        valid_for=timedelta(minutes=15),
    )
    state = MacroContextService().build_state(evidence, NOW)

    class Provider:
        model_id = "synthetic-news-model"

        def analyze(self, _request):
            return {
                "directional_bias": "unknown",
                "event_risk": "medium",
                "confidence": 0.4,
                "summary": "Official headline metadata warrants caution.",
                "risk_flags": ["UNASSESSED_NEWS_CONTEXT"],
                "source_signal_ids": ["news:evidence"],
            }

    result = build_market_context_snapshot(
        snapshot_id="NEWS-AI-1",
        instrument_id="GLOBAL-MARKET-CONTEXT",
        macro_state=state,
        generated_at_utc=NOW,
        valid_for=timedelta(minutes=10),
        prompt_version="openai-market-context-v1",
        provider=Provider(),
    )

    assert result.ai_analysis.status is AIAnalysisStatus.AVAILABLE
    assert result.ai_analysis.directional_bias is DirectionalBias.UNKNOWN
    assert result.ai_analysis.event_risk is EventRisk.MEDIUM
    assert state.event_risk is EventRisk.UNKNOWN


def test_news_collection_expiry_is_not_extended_by_later_context_rebuild() -> None:
    collection = NewsCollectionSnapshot(
        schema_version=1,
        provider_id="official-provider",
        status=ProviderCollectionStatus.AVAILABLE,
        items=(_news_item("evidence", 10),),
        collected_at_utc=NOW,
        reason_codes=(),
    )
    signals = build_news_ai_evidence_signals(
        (collection,), generated_at_utc=NOW + timedelta(minutes=10), valid_for=timedelta(minutes=15)
    )
    assert len(signals) == 1
    assert signals[0].valid_until_utc == NOW + timedelta(minutes=15)
    assert not build_news_ai_evidence_signals(
        (collection,), generated_at_utc=NOW + timedelta(minutes=15), valid_for=timedelta(minutes=15)
    )
    assert not build_news_ai_evidence_signals(
        (collection,), generated_at_utc=NOW - timedelta(seconds=1), valid_for=timedelta(minutes=15)
    )


def test_ai_evidence_limit_keeps_discovery_provider_represented() -> None:
    official = NewsCollectionSnapshot(
        schema_version=1,
        provider_id="official-provider",
        status=ProviderCollectionStatus.AVAILABLE,
        items=tuple(_news_item(f"official-{index}", index) for index in range(30)),
        collected_at_utc=NOW,
        reason_codes=(),
    )
    tavily = NewsCollectionSnapshot(
        schema_version=1,
        provider_id="tavily-news",
        status=ProviderCollectionStatus.AVAILABLE,
        items=tuple(_news_item(f"tavily-{index}", 120 + index) for index in range(5)),
        collected_at_utc=NOW,
        reason_codes=(),
    )

    signals = build_news_ai_evidence_signals(
        (official, tavily),
        generated_at_utc=NOW,
        valid_for=timedelta(hours=24),
        max_items=20,
    )

    assert len(signals) == 20
    tavily_signals = tuple(
        signal for signal in signals if "provider:tavily-news" in signal.tags
    )
    assert len(tavily_signals) == 5
    assert all("discovery_news_metadata" in signal.tags for signal in tavily_signals)


def test_article_selection_deduplicates_urls_and_keeps_five_diverse_sources() -> None:
    duplicate_a = _record("duplicate-a", url_suffix="same?utm_source=a", relevance=0.6)
    duplicate_b = _record("duplicate-b", url_suffix="same?utm_source=b", relevance=0.9)
    records = (
        duplicate_a,
        duplicate_b,
        *(
            _record(
                f"item-{index}",
                source=f"source-{index}.example",
                relevance=0.85 - index / 100,
            )
            for index in range(6)
        ),
    )

    selected = select_ai_article_candidates(
        records,
        generated_at_utc=NOW,
        freshness_policy=IntelligenceFreshnessPolicy(),
    )

    assert len(selected) == 5
    assert not {"duplicate-a", "duplicate-b"}.issubset(
        {record.news.item_id for record in selected}
    )
    assert len({record.news.source for record in selected}) >= 4


def test_category_freshness_retains_active_monetary_policy_beyond_breaking_window() -> None:
    records = (
        _record("stale-breaking", hours_ago=8),
        _record(
            "active-policy",
            category=ContextCategory.CENTRAL_BANK,
            hours_ago=48,
        ),
    )

    selected = select_ai_article_candidates(
        records,
        generated_at_utc=NOW,
        freshness_policy=IntelligenceFreshnessPolicy(),
    )

    assert tuple(record.news.item_id for record in selected) == ("active-policy",)
