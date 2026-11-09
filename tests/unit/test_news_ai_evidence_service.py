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
from trading_ig_assistant.services.ai_context_service import build_market_context_snapshot
from trading_ig_assistant.services.macro_context_service import MacroContextService
from trading_ig_assistant.services.news_ai_evidence_service import (
    build_news_ai_evidence_signals,
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
