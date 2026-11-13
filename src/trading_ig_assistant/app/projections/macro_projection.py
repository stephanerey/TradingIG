"""Project normalized official-source metadata without deriving market sentiment."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from trading_ig_assistant.app.projections.common import Availability
from trading_ig_assistant.app.projections.macro import (
    AIEvidenceRowVM,
    IntelligenceEventRowVM,
    MacroVM,
    NewsRowVM,
)
from trading_ig_assistant.domain.ai_context import AIAnalysisStatus, MarketContextSnapshot
from trading_ig_assistant.domain.context_sources import (
    NewsCollectionSnapshot,
    ProviderCollectionStatus,
)
from trading_ig_assistant.domain.market_intelligence import (
    ArticleEvidenceBundle,
    IntelligenceCoverageStatus,
    MarketIntelligenceSnapshot,
    ResearchQuotaView,
)


def build_macro_projection(
    *,
    generation_id: int,
    snapshots: tuple[NewsCollectionSnapshot, ...],
    generated_at_utc: datetime,
    ai_snapshot: MarketContextSnapshot | None = None,
    ai_evidence: ArticleEvidenceBundle | None = None,
    ai_preview: ArticleEvidenceBundle | None = None,
    intelligence_snapshot: MarketIntelligenceSnapshot | None = None,
    quota: ResearchQuotaView | None = None,
    tavily_collection_status: ProviderCollectionStatus = ProviderCollectionStatus.UNAVAILABLE,
    gdelt_collection_status: ProviderCollectionStatus = ProviderCollectionStatus.UNAVAILABLE,
) -> MacroVM:
    rows = tuple(
        sorted(
            (
                NewsRowVM(
                    item_id=item.item_id,
                    headline=item.headline,
                    source=item.source,
                    published_at_utc=item.published_at_utc,
                    category=item.category.value,
                    importance=item.importance.value,
                    usage_rights=item.usage_rights.value,
                    source_url=item.source_url,
                    provider_id=snapshot.provider_id,
                )
                for snapshot in snapshots
                for item in snapshot.items
            ),
            key=lambda row: row.published_at_utc,
            reverse=True,
        )
    )
    available = tuple(
        snapshot
        for snapshot in snapshots
        if snapshot.status is ProviderCollectionStatus.AVAILABLE
    )
    reasons = tuple(
        dict.fromkeys(
            reason
            for snapshot in snapshots
            for reason in snapshot.reason_codes
        )
    )
    ai = ai_snapshot.ai_analysis if ai_snapshot is not None else None
    ai_available = ai is not None and ai.status is AIAnalysisStatus.AVAILABLE
    ai_ready = ai_available and ai.valid_until_utc > generated_at_utc
    ai_status = (
        Availability.READY
        if ai_ready
        else Availability.STALE
        if ai_available
        else Availability.UNAVAILABLE
    )
    intelligence_status = _intelligence_availability(intelligence_snapshot)
    intelligence_events = (
        ()
        if intelligence_snapshot is None
        else tuple(
            IntelligenceEventRowVM(
                event_id=event.event_id,
                headline=event.headline,
                published_at_utc=event.published_at_utc,
                publication_time_status=event.publication_time_status.value,
                verification_status=event.verification_status.value,
                category=event.category.value,
                sources=event.source_names,
                source_urls=event.source_urls,
            )
            for event in intelligence_snapshot.events
        )
    )
    provider_counts = Counter(row.provider_id for row in rows)
    category_counts = Counter(row.category for row in rows)
    tavily_count = provider_counts.get("tavily-news", 0)
    gdelt_count = provider_counts.get("gdelt-doc", 0)
    return MacroVM(
        generation_id=generation_id,
        generated_at_utc=generated_at_utc,
        news_status=(Availability.READY if available else Availability.UNAVAILABLE),
        news_rows=rows,
        news_provider_count=len(snapshots),
        news_reason_codes=reasons,
        news_collected_at_utc=(
            max(snapshot.collected_at_utc for snapshot in snapshots)
            if snapshots
            else None
        ),
        ai_status=ai_status,
        ai_model_id=ai.model_id if ai is not None else None,
        ai_prompt_version=ai.prompt_version if ai is not None else None,
        ai_scope=ai.market_scope if ai is not None else None,
        ai_summary=ai.summary if ai is not None else None,
        ai_directional_bias=ai.directional_bias.value if ai is not None else None,
        ai_event_risk=ai.event_risk.value if ai is not None else None,
        ai_confidence=ai.confidence if ai is not None else None,
        ai_risk_flags=ai.risk_flags if ai is not None else (),
        ai_source_signal_ids=ai.source_signal_ids if ai is not None else (),
        ai_generated_at_utc=ai.generated_at_utc if ai is not None else None,
        ai_valid_until_utc=ai.valid_until_utc if ai is not None else None,
        ai_reason_codes=(
            tuple(code for code in ai_snapshot.reason_codes if code.startswith("AI_"))
            if ai_snapshot is not None
            else ("AI_NOT_REQUESTED",)
        ),
        intelligence_status=intelligence_status,
        intelligence_events=intelligence_events,
        intelligence_reason_codes=(
            intelligence_snapshot.reason_codes
            if intelligence_snapshot is not None
            else ("MARKET_INTELLIGENCE_NOT_COLLECTED",)
        ),
        tavily_status=_provider_availability(tavily_collection_status),
        gdelt_status=_provider_availability(gdelt_collection_status),
        tavily_credits_used=quota.used_credits if quota is not None else 0,
        tavily_credits_today=quota.used_today if quota is not None else 0,
        tavily_credits_remaining=quota.remaining_credits if quota is not None else 900,
        tavily_monthly_limit=quota.hard_limit if quota is not None else 900,
        official_news_count=max(0, len(rows) - tavily_count - gdelt_count),
        tavily_news_count=tavily_count,
        gdelt_news_count=gdelt_count,
        category_counts=tuple(sorted(category_counts.items())),
        ai_evidence_rows=(
            ()
            if ai_evidence is None
            else tuple(
                AIEvidenceRowVM(
                    signal_id=article.signal_id,
                    headline=article.headline,
                    source=article.source,
                    source_url=article.source_url,
                    excerpt=article.excerpt or "",
                    content_origin=article.content_origin.value,
                    published_at_utc=article.published_at_utc,
                )
                for article in ai_evidence.articles
            )
        ),
        ai_estimated_input_tokens=(
            ai_evidence.estimated_input_tokens if ai_evidence is not None else 0
        ),
        ai_estimated_output_tokens=(
            ai_evidence.estimated_output_tokens if ai_evidence is not None else 0
        ),
        ai_estimated_cost_usd=(
            ai_evidence.estimated_openai_cost_usd if ai_evidence is not None else 0.0
        ),
        ai_tavily_extract_credits=(
            ai_evidence.tavily_extract_credits if ai_evidence is not None else 0
        ),
        ai_preview_source_count=(len(ai_preview.articles) if ai_preview is not None else 0),
        ai_preview_input_tokens=(
            ai_preview.estimated_input_tokens if ai_preview is not None else 0
        ),
        ai_preview_estimated_cost_usd=(
            ai_preview.estimated_openai_cost_usd if ai_preview is not None else 0.0
        ),
        ai_preview_tavily_extract_credits=(
            ai_preview.tavily_extract_credits if ai_preview is not None else 0
        ),
    )


def _provider_availability(status: ProviderCollectionStatus) -> Availability:
    return (
        Availability.READY
        if status is ProviderCollectionStatus.AVAILABLE
        else Availability.UNAVAILABLE
    )


def _intelligence_availability(
    snapshot: MarketIntelligenceSnapshot | None,
) -> Availability:
    if snapshot is None:
        return Availability.UNAVAILABLE
    return {
        IntelligenceCoverageStatus.FRESH: Availability.READY,
        IntelligenceCoverageStatus.STALE: Availability.STALE,
        IntelligenceCoverageStatus.DEGRADED: Availability.DATA_GAP,
        IntelligenceCoverageStatus.UNAVAILABLE: Availability.UNAVAILABLE,
    }[snapshot.coverage_status]
