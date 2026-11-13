"""Synchronous orchestration run behind a Qt worker boundary."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Protocol

from trading_ig_assistant.adapters.news_provider import NewsProvider
from trading_ig_assistant.domain.context_sources import (
    ContextCategory,
    NewsCollectionSnapshot,
    ProviderCollectionStatus,
)
from trading_ig_assistant.domain.market_intelligence import (
    ArticleEvidenceBundle,
    IntelligenceNewsRecord,
    IntelligenceProviderKind,
    IntelligenceProviderResult,
    MarketIntelligenceSnapshot,
    NewsSearchRequest,
    PublicationTimeStatus,
    ResearchQuotaView,
    ResearchTrigger,
    VerificationStatus,
)
from trading_ig_assistant.services.market_intelligence_scheduler import (
    DEFAULT_INTELLIGENCE_SCHEDULES,
    IntelligenceFreshnessPolicy,
    IntelligenceSchedule,
    IntelligenceTheme,
    MarketIntelligenceScheduler,
)
from trading_ig_assistant.services.market_intelligence_service import (
    build_market_intelligence_snapshot,
)
from trading_ig_assistant.services.news_ai_evidence_service import (
    article_evidence_needing_extract,
    build_article_evidence_bundle,
    select_ai_article_candidates,
)
from trading_ig_assistant.services.news_collection_service import collect_news
from trading_ig_assistant.services.research_quota_service import ResearchQuotaManager


class QueryNewsProvider(Protocol):
    @property
    def provider_id(self) -> str: ...

    def search_news(
        self,
        request: NewsSearchRequest,
        *,
        as_of_utc: datetime,
    ) -> IntelligenceProviderResult: ...


class ArticleExtractProvider(Protocol):
    def extract(self, urls: tuple[str, ...], *, query: str | None = None): ...


@dataclass(frozen=True)
class MarketIntelligenceRefreshResult:
    news_snapshots: tuple[NewsCollectionSnapshot, ...]
    intelligence: MarketIntelligenceSnapshot
    quota: ResearchQuotaView
    tavily_status: ProviderCollectionStatus
    gdelt_status: ProviderCollectionStatus


class MarketIntelligenceRuntime:
    """Collect official and discovery metadata without any execution capability."""

    def __init__(
        self,
        *,
        official_providers: tuple[NewsProvider, ...],
        gdelt_provider: QueryNewsProvider | None,
        quota_manager: ResearchQuotaManager,
        tavily_provider: QueryNewsProvider | None = None,
        tavily_extractor: ArticleExtractProvider | None = None,
        scheduler: MarketIntelligenceScheduler | None = None,
        freshness_policy: IntelligenceFreshnessPolicy | None = None,
    ) -> None:
        self._official_providers = official_providers
        self._gdelt_provider = gdelt_provider
        self._tavily_provider = tavily_provider
        self._tavily_extractor = tavily_extractor
        self._quota_manager = quota_manager
        self._scheduler = scheduler or MarketIntelligenceScheduler()
        self._freshness_policy = freshness_policy or IntelligenceFreshnessPolicy()
        self._cached_results: dict[str, IntelligenceProviderResult] = {}
        self._scheduled_attempts: dict[IntelligenceTheme, datetime] = {}
        self._gdelt_retry_after_utc: datetime | None = None
        self._gdelt_consecutive_failures = 0
        self._latest_official_records: tuple[IntelligenceNewsRecord, ...] = ()

    def set_tavily_provider(self, provider: QueryNewsProvider | None) -> None:
        """Replace the optional discovery provider without restarting the GUI."""

        self._tavily_provider = provider
        if provider is None:
            self._cached_results = {
                key: value
                for key, value in self._cached_results.items()
                if value.provider_id != "tavily-news"
            }

    def set_tavily_extractor(self, provider: ArticleExtractProvider | None) -> None:
        self._tavily_extractor = provider

    def set_gdelt_provider(self, provider: QueryNewsProvider | None) -> None:
        """Enable or disable public GDELT discovery without restarting."""

        self._gdelt_provider = provider
        self._gdelt_retry_after_utc = None
        self._gdelt_consecutive_failures = 0
        if provider is None:
            self._cached_results = {
                key: value
                for key, value in self._cached_results.items()
                if value.provider_id != "gdelt-doc"
            }

    def refresh(
        self,
        *,
        as_of_utc: datetime,
        trigger: ResearchTrigger = ResearchTrigger.MANUAL,
        tavily_request: NewsSearchRequest | None = None,
        gdelt_request: NewsSearchRequest | None = None,
    ) -> MarketIntelligenceRefreshResult:
        _require_utc(as_of_utc)
        official = tuple(
            collect_news(provider, as_of_utc=as_of_utc)
            for provider in self._official_providers
        )
        self._latest_official_records = tuple(
            IntelligenceNewsRecord(
                news=item,
                provider_id=snapshot.provider_id,
                provider_kind=IntelligenceProviderKind.OFFICIAL,
                publication_time_status=PublicationTimeStatus.REPORTED,
                verification_status=VerificationStatus.OFFICIAL,
                relevance_score=1.0,
                search_excerpt=item.summary,
            )
            for snapshot in official
            if snapshot.status is ProviderCollectionStatus.AVAILABLE
            for item in snapshot.items
        )
        reasons: list[str] = []
        due_schedules = (
            self._due_schedules(as_of_utc)
            if trigger is ResearchTrigger.SCHEDULED
            else ()
        )
        collect_gdelt = self._gdelt_provider is not None and (
            trigger is not ResearchTrigger.SCHEDULED
            or gdelt_request is not None
            or any(
                schedule.theme is IntelligenceTheme.GLOBAL_GEOPOLITICS
                for schedule in due_schedules
            )
        )
        gdelt_backoff_active = (
            self._gdelt_retry_after_utc is not None
            and as_of_utc < self._gdelt_retry_after_utc
        )
        if collect_gdelt and gdelt_backoff_active:
            reasons.append("GDELT_CIRCUIT_OPEN")
        elif collect_gdelt:
            gdelt_query = gdelt_request or NewsSearchRequest(
                "geopolitical crisis OR sanctions OR conflict OR energy supply disruption",
                ContextCategory.GEOPOLITICAL,
                recent_window=self._freshness_policy.geopolitics,
            )
            try:
                gdelt_result = self._gdelt_provider.search_news(
                    gdelt_query,
                    as_of_utc=as_of_utc,
                )
            except Exception as exc:
                reason = getattr(exc, "reason_code", "GDELT_PROVIDER_ERROR")
                reasons.append(reason)
                self._gdelt_consecutive_failures += 1
                explicit_retry = getattr(exc, "retry_after_seconds", None)
                if isinstance(explicit_retry, int) and explicit_retry > 0:
                    delay = timedelta(seconds=min(explicit_retry, 3_600))
                else:
                    base_seconds = 900 if reason == "GDELT_RATE_LIMITED" else 60
                    delay = timedelta(
                        seconds=min(
                            3_600,
                            base_seconds * (2 ** (self._gdelt_consecutive_failures - 1)),
                        )
                    )
                self._gdelt_retry_after_utc = as_of_utc + delay
            else:
                self._gdelt_retry_after_utc = None
                self._gdelt_consecutive_failures = 0
                self._cached_results["gdelt-doc:global"] = gdelt_result
        elif self._gdelt_provider is None:
            reasons.append("GDELT_PROVIDER_DISABLED")

        tavily_requests = self._tavily_requests(
            trigger=trigger,
            explicit=tavily_request,
            due_schedules=due_schedules,
        )
        if self._tavily_provider is None:
            reasons.append("TAVILY_API_KEY_MISSING")
        else:
            for cache_key, query in tavily_requests:
                reservation = self._quota_manager.reserve(
                    trigger=trigger,
                    now_utc=as_of_utc,
                )
                if not reservation.allowed:
                    reasons.append(reservation.reason_code)
                    break
                try:
                    tavily_result = self._tavily_provider.search_news(
                        query,
                        as_of_utc=as_of_utc,
                    )
                except Exception as exc:
                    reasons.append(getattr(exc, "reason_code", "TAVILY_PROVIDER_ERROR"))
                else:
                    if cache_key == "tavily-news:manual":
                        tavily_result = _classify_manual_tavily_result(tavily_result)
                    merged_result = _merge_recent_result(
                        previous=self._cached_results.get(cache_key),
                        current=tavily_result,
                        recent_window=query.recent_window,
                        as_of_utc=as_of_utc,
                    )
                    self._cached_results[cache_key] = _filter_result_by_freshness(
                        merged_result,
                        freshness_policy=self._freshness_policy,
                        as_of_utc=as_of_utc,
                    )
                    if tavily_result.usage is not None:
                        self._quota_manager.reconcile(
                            reserved_credits=reservation.reserved_credits,
                            actual_credits=tavily_result.usage.credits,
                            now_utc=as_of_utc,
                        )

        for schedule in due_schedules:
            self._scheduled_attempts[schedule.theme] = as_of_utc

        results = tuple(self._cached_results.values())
        gdelt_results = tuple(
            result
            for result in results
            if result.provider_id == "gdelt-doc" and result.records
        )
        tavily_results = tuple(
            result
            for result in results
            if result.provider_id == "tavily-news" and result.records
        )
        if not tavily_results and not any(reason.startswith("TAVILY") for reason in reasons):
            reasons.append("TAVILY_EMPTY")
        gdelt_status = (
            ProviderCollectionStatus.AVAILABLE
            if gdelt_results
            else ProviderCollectionStatus.UNAVAILABLE
        )
        tavily_status = (
            ProviderCollectionStatus.AVAILABLE
            if tavily_results
            else ProviderCollectionStatus.UNAVAILABLE
        )
        snapshots = list(official)
        if gdelt_results:
            snapshots.append(_merged_result_snapshot("gdelt-doc", gdelt_results, as_of_utc))
        else:
            snapshots.append(
                _unavailable_snapshot(
                    "gdelt-doc",
                    as_of_utc,
                    reasons[-1] if reasons and reasons[-1].startswith("GDELT") else "GDELT_EMPTY",
                )
            )
        if tavily_results:
            snapshots.append(
                _merged_result_snapshot("tavily-news", tavily_results, as_of_utc)
            )
        else:
            tavily_reason = next(
                (reason for reason in reversed(reasons) if reason.startswith("TAVILY")),
                "TAVILY_EMPTY",
            )
            snapshots.append(_unavailable_snapshot("tavily-news", as_of_utc, tavily_reason))

        quota = self._quota_manager.inspect(now_utc=as_of_utc)
        intelligence = build_market_intelligence_snapshot(
            provider_results=results,
            official_snapshots=official,
            generated_at_utc=as_of_utc,
            reason_codes=tuple(reasons),
        )
        return MarketIntelligenceRefreshResult(
            news_snapshots=tuple(snapshots),
            intelligence=intelligence,
            quota=quota,
            tavily_status=tavily_status,
            gdelt_status=gdelt_status,
        )

    def prepare_ai_evidence(
        self,
        *,
        as_of_utc: datetime,
        model: str,
        max_output_tokens: int,
    ) -> ArticleEvidenceBundle:
        """Build at most five transient article excerpts after explicit user consent."""

        _require_utc(as_of_utc)
        records = tuple(
            record
            for result in self._cached_results.values()
            for record in result.records
        ) + self._latest_official_records
        selected = select_ai_article_candidates(
            records,
            generated_at_utc=as_of_utc,
            freshness_policy=self._freshness_policy,
        )
        if not selected:
            raise ValueError("no recent article candidates are available")
        extract_urls = article_evidence_needing_extract(selected)
        extracted: dict[str, str] = {}
        extract_credits = 0
        reasons: list[str] = []
        if extract_urls and self._tavily_extractor is not None:
            reservation = self._quota_manager.reserve(
                trigger=ResearchTrigger.MANUAL,
                now_utc=as_of_utc,
                credits=1,
            )
            if reservation.allowed:
                try:
                    result = self._tavily_extractor.extract(
                        extract_urls[:5],
                        query="market impact macroeconomic geopolitical monetary policy",
                    )
                except Exception as exc:
                    reasons.append(getattr(exc, "reason_code", "TAVILY_EXTRACT_ERROR"))
                else:
                    extracted = {article.url: article.content for article in result.articles}
                    extract_credits = result.usage.credits
                    self._quota_manager.reconcile(
                        reserved_credits=reservation.reserved_credits,
                        actual_credits=extract_credits,
                        now_utc=as_of_utc,
                    )
                    if result.failed_urls:
                        reasons.append("TAVILY_EXTRACT_PARTIAL")
            else:
                reasons.append(reservation.reason_code)
        elif extract_urls:
            reasons.append("TAVILY_EXTRACT_UNAVAILABLE")
        return build_article_evidence_bundle(
            selected,
            generated_at_utc=as_of_utc,
            freshness_policy=self._freshness_policy,
            extracted_content=extracted,
            max_output_tokens=max_output_tokens,
            model=model,
            tavily_extract_credits=extract_credits,
            reason_codes=tuple(reasons),
        )

    def preview_ai_evidence(
        self,
        *,
        as_of_utc: datetime,
        model: str,
        max_output_tokens: int,
    ) -> ArticleEvidenceBundle:
        """Estimate the bounded payload without extracting or transmitting content."""

        _require_utc(as_of_utc)
        records = tuple(
            record
            for result in self._cached_results.values()
            for record in result.records
        ) + self._latest_official_records
        selected = select_ai_article_candidates(
            records,
            generated_at_utc=as_of_utc,
            freshness_policy=self._freshness_policy,
        )
        if not selected:
            raise ValueError("no recent article candidates are available")
        extract_count = len(article_evidence_needing_extract(selected))
        return build_article_evidence_bundle(
            selected,
            generated_at_utc=as_of_utc,
            freshness_policy=self._freshness_policy,
            max_output_tokens=max_output_tokens,
            model=model,
            tavily_extract_credits=1 if extract_count else 0,
            reason_codes=("AI_EVIDENCE_PREVIEW",),
        )

    def _due_schedules(self, as_of_utc: datetime) -> tuple[IntelligenceSchedule, ...]:
        quota = self._quota_manager.inspect(now_utc=as_of_utc)
        return tuple(
            schedule
            for schedule in DEFAULT_INTELLIGENCE_SCHEDULES
            if self._scheduler.decide(
                trigger=ResearchTrigger.SCHEDULED,
                now_utc=as_of_utc,
                quota=quota,
                schedule=schedule,
                last_completed_at_utc=self._scheduled_attempts.get(schedule.theme),
            ).allowed
        )

    def _tavily_requests(
        self,
        *,
        trigger: ResearchTrigger,
        explicit: NewsSearchRequest | None,
        due_schedules: tuple[IntelligenceSchedule, ...],
    ) -> tuple[tuple[str, NewsSearchRequest], ...]:
        if explicit is not None:
            return (("tavily-news:explicit", explicit),)
        if trigger is ResearchTrigger.SCHEDULED:
            return tuple(
                (
                    f"tavily-news:{schedule.theme.value}",
                    NewsSearchRequest(
                        schedule.query,
                        schedule.category,
                        recent_window=self._freshness_policy.for_category(
                            schedule.category
                        ),
                    ),
                )
                for schedule in due_schedules
            )
        return (
            (
                "tavily-news:manual",
                NewsSearchRequest(
                    (
                        "latest market-moving global financial news affecting equities, "
                        "interest rates, energy, gold and geopolitical risk"
                    ),
                    ContextCategory.OTHER,
                    max_results=10,
                    # Retrieve the broadest configured horizon once, then classify
                    # and apply the category-specific windows locally. This keeps a
                    # manual refresh to one Tavily Search credit.
                    recent_window=self._freshness_policy.geopolitics,
                ),
            ),
        )


def _merged_result_snapshot(
    provider_id: str,
    results: tuple[IntelligenceProviderResult, ...],
    observed_at_utc: datetime,
) -> NewsCollectionSnapshot:
    items_by_id = {
        record.news.item_id: record.news
        for result in results
        for record in result.records
    }
    return NewsCollectionSnapshot(
        schema_version=1,
        provider_id=provider_id,
        status=ProviderCollectionStatus.AVAILABLE,
        items=tuple(
            sorted(
                items_by_id.values(),
                key=lambda item: (item.published_at_utc, item.item_id),
                reverse=True,
            )
        ),
        collected_at_utc=observed_at_utc,
        reason_codes=(),
    )


def _merge_recent_result(
    *,
    previous: IntelligenceProviderResult | None,
    current: IntelligenceProviderResult,
    recent_window: timedelta | None,
    as_of_utc: datetime,
) -> IntelligenceProviderResult:
    """Keep a stable rolling result set without retaining stale discoveries."""

    if (
        previous is None
        or recent_window is None
        or previous.provider_id != current.provider_id
        or previous.provider_kind is not current.provider_kind
        or previous.query != current.query
    ):
        return current
    oldest_allowed = as_of_utc - recent_window
    records_by_id = {
        record.news.item_id: record
        for record in (*previous.records, *current.records)
        if oldest_allowed <= record.news.published_at_utc <= as_of_utc
    }
    records = tuple(
        sorted(
            records_by_id.values(),
            key=lambda record: (record.news.published_at_utc, record.news.item_id),
            reverse=True,
        )[:10]
    )
    return IntelligenceProviderResult(
        provider_id=current.provider_id,
        provider_kind=current.provider_kind,
        query=current.query,
        records=records,
        observed_at_utc=current.observed_at_utc,
        usage=current.usage,
        request_id=current.request_id,
    )


def _classify_manual_tavily_result(
    result: IntelligenceProviderResult,
) -> IntelligenceProviderResult:
    """Assign a freshness family to broad manual-search discoveries."""

    records = tuple(
        replace(
            record,
            news=replace(
                record.news,
                category=_infer_news_category(record),
                tags=tuple(dict.fromkeys((*record.news.tags, "category:inferred"))),
            ),
        )
        for record in result.records
    )
    return replace(result, records=records)


def _infer_news_category(record: IntelligenceNewsRecord) -> ContextCategory:
    text = f"{record.news.headline} {record.search_excerpt or ''}".casefold()
    keyword_groups = (
        (
            ContextCategory.GEOPOLITICAL,
            (
                "geopolit",
                "sanction",
                "conflict",
                "war ",
                "ukraine",
                "russia",
                "iran",
                "israel",
                "gaza",
                "taiwan",
                "nato",
                "trade restriction",
            ),
        ),
        (
            ContextCategory.CENTRAL_BANK,
            (
                "central bank",
                "federal reserve",
                "the fed",
                "ecb",
                "bank of england",
                "monetary policy",
                "rate cut",
                "rate hike",
                "interest rate",
            ),
        ),
        (ContextCategory.INFLATION, ("inflation", "consumer price", " cpi", " pce")),
        (
            ContextCategory.EMPLOYMENT,
            ("employment", "unemployment", "payroll", "jobs report", "labor market"),
        ),
        (
            ContextCategory.GROWTH,
            ("gross domestic product", " gdp", "recession", "economic growth", " pmi"),
        ),
        (
            ContextCategory.ENERGY,
            ("oil", "crude", "opec", "natural gas", "energy supply"),
        ),
    )
    for category, keywords in keyword_groups:
        if any(keyword in text for keyword in keywords):
            return category
    return ContextCategory.OTHER


def _filter_result_by_freshness(
    result: IntelligenceProviderResult,
    *,
    freshness_policy: IntelligenceFreshnessPolicy,
    as_of_utc: datetime,
) -> IntelligenceProviderResult:
    records = tuple(
        record
        for record in result.records
        if timedelta(0)
        <= as_of_utc - record.news.published_at_utc
        <= freshness_policy.for_category(record.news.category)
    )
    return replace(result, records=records)


def _unavailable_snapshot(
    provider_id: str,
    observed_at_utc: datetime,
    reason_code: str,
) -> NewsCollectionSnapshot:
    return NewsCollectionSnapshot(
        schema_version=1,
        provider_id=provider_id,
        status=ProviderCollectionStatus.UNAVAILABLE,
        items=(),
        collected_at_utc=observed_at_utc,
        reason_codes=(reason_code,),
    )


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("market intelligence runtime timestamp must use UTC")
