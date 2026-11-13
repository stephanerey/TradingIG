from datetime import UTC, datetime, timedelta

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.adapters.gdelt_news import GdeltNewsError
from trading_ig_assistant.app.projections.common import Availability
from trading_ig_assistant.app.projections.macro_projection import build_macro_projection
from trading_ig_assistant.app.qt_macro_context_controller import MacroContextController
from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
from trading_ig_assistant.domain.context_sources import (
    ContextCategory,
    ContextImportance,
    NewsItem,
    SourceUsageRights,
)
from trading_ig_assistant.domain.market_intelligence import (
    IntelligenceNewsRecord,
    IntelligenceProviderKind,
    IntelligenceProviderResult,
    ProviderUsage,
    PublicationTimeStatus,
    VerificationStatus,
)
from trading_ig_assistant.persistence.research_quota_store import JsonResearchQuotaStore
from trading_ig_assistant.services.market_intelligence_runtime import (
    MarketIntelligenceRuntime,
)
from trading_ig_assistant.services.research_quota_service import ResearchQuotaManager

NOW = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _news(item_id: str, source: str, url: str) -> NewsItem:
    return NewsItem(
        schema_version=1,
        item_id=item_id,
        headline=f"Market event {item_id}",
        summary=None,
        category=ContextCategory.GEOPOLITICAL,
        importance=ContextImportance.UNKNOWN,
        published_at_utc=NOW - timedelta(minutes=10),
        observed_at_utc=NOW,
        source=source,
        source_url=url,
        usage_rights=SourceUsageRights.METADATA_ONLY,
        tags=(source,),
    )


class OfficialProvider:
    provider_id = "official-test"

    def fetch_news(self, *, as_of_utc: datetime):
        assert as_of_utc == NOW
        return (_news("official", "Official Source", "https://official.example/release"),)


class QueryProvider:
    def __init__(self, provider_id, kind, verification, *, credits=None):
        self.provider_id = provider_id
        self.kind = kind
        self.verification = verification
        self.credits = credits
        self.calls = 0

    def search_news(self, request, *, as_of_utc):
        self.calls += 1
        news = _news(
            self.provider_id,
            f"{self.provider_id}.example",
            f"https://{self.provider_id}.example/story",
        )
        record = IntelligenceNewsRecord(
            news,
            self.provider_id,
            self.kind,
            PublicationTimeStatus.PROVIDER_ESTIMATE,
            self.verification,
        )
        return IntelligenceProviderResult(
            self.provider_id,
            self.kind,
            request.query,
            (record,),
            as_of_utc,
            ProviderUsage(self.credits) if self.credits is not None else None,
        )


class ChangingTavilyProvider(QueryProvider):
    def search_news(self, request, *, as_of_utc):
        self.calls += 1
        item_id = f"tavily-{self.calls}"
        news = NewsItem(
            schema_version=1,
            item_id=item_id,
            headline=f"Market event {item_id}",
            summary=None,
            category=ContextCategory.OTHER,
            importance=ContextImportance.UNKNOWN,
            published_at_utc=as_of_utc - timedelta(minutes=self.calls),
            observed_at_utc=as_of_utc,
            source="tavily.example",
            source_url=f"https://tavily.example/{item_id}",
            usage_rights=SourceUsageRights.METADATA_ONLY,
            tags=("tavily-news",),
        )
        return IntelligenceProviderResult(
            self.provider_id,
            self.kind,
            request.query,
            (
                IntelligenceNewsRecord(
                    news,
                    self.provider_id,
                    self.kind,
                    PublicationTimeStatus.PROVIDER_ESTIMATE,
                    self.verification,
                ),
            ),
            as_of_utc,
            ProviderUsage(1),
        )


def _runtime(tmp_path):
    gdelt = QueryProvider(
        "gdelt-doc",
        IntelligenceProviderKind.GDELT,
        VerificationStatus.UNCONFIRMED,
    )
    tavily = QueryProvider(
        "tavily-news",
        IntelligenceProviderKind.TAVILY,
        VerificationStatus.SINGLE_SOURCE,
        credits=1,
    )
    runtime = MarketIntelligenceRuntime(
        official_providers=(OfficialProvider(),),
        gdelt_provider=gdelt,
        tavily_provider=tavily,
        quota_manager=ResearchQuotaManager(
            JsonResearchQuotaStore(tmp_path / "quota.json")
        ),
    )
    return runtime, gdelt, tavily


def test_runtime_composes_official_gdelt_tavily_and_persists_credit(tmp_path) -> None:
    runtime, gdelt, tavily = _runtime(tmp_path)

    result = runtime.refresh(as_of_utc=NOW)

    assert gdelt.calls == tavily.calls == 1
    assert result.quota.used_credits == 1
    assert result.tavily_status.value == "available"
    assert result.gdelt_status.value == "available"
    assert len(result.news_snapshots) == 3
    assert len(result.intelligence.events) == 3

    projection = build_macro_projection(
        generation_id=1,
        snapshots=result.news_snapshots,
        generated_at_utc=NOW,
        intelligence_snapshot=result.intelligence,
        quota=result.quota,
        tavily_collection_status=result.tavily_status,
        gdelt_collection_status=result.gdelt_status,
    )
    assert projection.intelligence_status is Availability.READY
    assert projection.tavily_status is Availability.READY
    assert projection.gdelt_status is Availability.READY
    assert projection.tavily_credits_used == 1
    assert len(projection.intelligence_events) == 3
    assert projection.official_news_count == 1
    assert projection.tavily_news_count == 1
    assert projection.gdelt_news_count == 1
    assert projection.category_counts == (("geopolitical", 2), ("other", 1))


def test_runtime_keeps_recent_tavily_results_stable_across_refreshes(tmp_path) -> None:
    tavily = ChangingTavilyProvider(
        "tavily-news",
        IntelligenceProviderKind.TAVILY,
        VerificationStatus.SINGLE_SOURCE,
        credits=1,
    )
    runtime = MarketIntelligenceRuntime(
        official_providers=(),
        gdelt_provider=None,
        tavily_provider=tavily,
        quota_manager=ResearchQuotaManager(
            JsonResearchQuotaStore(tmp_path / "quota.json")
        ),
    )

    runtime.refresh(as_of_utc=NOW)
    result = runtime.refresh(as_of_utc=NOW + timedelta(minutes=1))

    tavily_snapshot = next(
        snapshot
        for snapshot in result.news_snapshots
        if snapshot.provider_id == "tavily-news"
    )
    assert tuple(item.item_id for item in tavily_snapshot.items) == (
        "tavily-2",
        "tavily-1",
    )


def test_manual_tavily_refresh_classifies_articles_before_applying_freshness(
    tmp_path,
) -> None:
    class MixedAgeTavily:
        provider_id = "tavily-news"

        def __init__(self) -> None:
            self.requests = []

        def search_news(self, request, *, as_of_utc):
            self.requests.append(request)

            def record(item_id: str, headline: str) -> IntelligenceNewsRecord:
                news = NewsItem(
                    schema_version=1,
                    item_id=item_id,
                    headline=headline,
                    summary=None,
                    category=ContextCategory.OTHER,
                    importance=ContextImportance.UNKNOWN,
                    published_at_utc=as_of_utc - timedelta(hours=48),
                    observed_at_utc=as_of_utc,
                    source="news.example",
                    source_url=f"https://news.example/{item_id}",
                    usage_rights=SourceUsageRights.METADATA_ONLY,
                    tags=("tavily-news",),
                )
                return IntelligenceNewsRecord(
                    news,
                    self.provider_id,
                    IntelligenceProviderKind.TAVILY,
                    PublicationTimeStatus.PROVIDER_ESTIMATE,
                    VerificationStatus.SINGLE_SOURCE,
                )

            return IntelligenceProviderResult(
                self.provider_id,
                IntelligenceProviderKind.TAVILY,
                request.query,
                (
                    record("monetary", "Federal Reserve monetary policy update"),
                    record("generic", "Equities finish mixed"),
                ),
                as_of_utc,
                ProviderUsage(1),
            )

    tavily = MixedAgeTavily()
    runtime = MarketIntelligenceRuntime(
        official_providers=(),
        gdelt_provider=None,
        tavily_provider=tavily,
        quota_manager=ResearchQuotaManager(JsonResearchQuotaStore(tmp_path / "quota.json")),
    )

    result = runtime.refresh(as_of_utc=NOW)

    assert len(tavily.requests) == 1
    assert tavily.requests[0].recent_window == timedelta(days=7)
    tavily_snapshot = next(
        snapshot
        for snapshot in result.news_snapshots
        if snapshot.provider_id == "tavily-news"
    )
    assert tuple(item.item_id for item in tavily_snapshot.items) == ("monetary",)
    assert tavily_snapshot.items[0].category is ContextCategory.CENTRAL_BANK
    assert result.tavily_status.value == "available"


def test_tavily_status_is_unavailable_when_search_yields_no_usable_article(
    tmp_path,
) -> None:
    class EmptyTavily:
        provider_id = "tavily-news"

        def search_news(self, request, *, as_of_utc):
            return IntelligenceProviderResult(
                self.provider_id,
                IntelligenceProviderKind.TAVILY,
                request.query,
                (),
                as_of_utc,
                ProviderUsage(1),
            )

    runtime = MarketIntelligenceRuntime(
        official_providers=(),
        gdelt_provider=None,
        tavily_provider=EmptyTavily(),
        quota_manager=ResearchQuotaManager(JsonResearchQuotaStore(tmp_path / "quota.json")),
    )

    result = runtime.refresh(as_of_utc=NOW)

    assert result.tavily_status.value == "unavailable"
    tavily_snapshot = next(
        snapshot
        for snapshot in result.news_snapshots
        if snapshot.provider_id == "tavily-news"
    )
    assert tavily_snapshot.status.value == "unavailable"
    assert tavily_snapshot.reason_codes == ("TAVILY_EMPTY",)


def test_gdelt_circuit_breaker_respects_retry_after_without_blocking_tavily(tmp_path) -> None:
    class RateLimitedGdelt:
        provider_id = "gdelt-doc"

        def __init__(self) -> None:
            self.calls = 0

        def search_news(self, request, *, as_of_utc):
            self.calls += 1
            raise GdeltNewsError(
                "rate limited",
                reason_code="GDELT_RATE_LIMITED",
                retry_after_seconds=120,
            )

    gdelt = RateLimitedGdelt()
    tavily = QueryProvider(
        "tavily-news",
        IntelligenceProviderKind.TAVILY,
        VerificationStatus.SINGLE_SOURCE,
        credits=1,
    )
    runtime = MarketIntelligenceRuntime(
        official_providers=(),
        gdelt_provider=gdelt,
        tavily_provider=tavily,
        quota_manager=ResearchQuotaManager(JsonResearchQuotaStore(tmp_path / "quota.json")),
    )

    first = runtime.refresh(as_of_utc=NOW)
    second = runtime.refresh(as_of_utc=NOW + timedelta(seconds=30))

    assert gdelt.calls == 1
    assert tavily.calls == 2
    assert "GDELT_RATE_LIMITED" in first.intelligence.reason_codes
    assert "GDELT_CIRCUIT_OPEN" in second.intelligence.reason_codes
    assert second.tavily_status.value == "available"


def test_qt_controller_runs_intelligence_runtime_off_gui_thread(tmp_path) -> None:
    app = _application()
    intelligence_runtime, _gdelt, _tavily = _runtime(tmp_path)
    runtime = TradingRuntime(now_provider=lambda: NOW)
    controller = MacroContextController(
        runtime=runtime,
        providers=(OfficialProvider(),),
        now_provider=lambda: NOW,
        intelligence_runtime=intelligence_runtime,
    )

    controller.refresh_news()
    loop = QtCore.QEventLoop()
    controller.busy_changed.connect(lambda busy: loop.quit() if not busy else None)
    QtCore.QTimer.singleShot(3000, loop.quit)
    loop.exec()
    app.processEvents()

    assert controller.busy is False
    projection = runtime.read_macro()
    assert projection.intelligence_status is Availability.READY
    assert projection.tavily_credits_used == 1


def test_macro_page_displays_provider_quota_and_deduplicated_events(tmp_path) -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.macro_page import MacroPage

    app = _application()
    runtime, _gdelt, _tavily = _runtime(tmp_path)
    result = runtime.refresh(as_of_utc=NOW)
    projection = build_macro_projection(
        generation_id=1,
        snapshots=result.news_snapshots,
        generated_at_utc=NOW,
        intelligence_snapshot=result.intelligence,
        quota=result.quota,
        tavily_collection_status=result.tavily_status,
        gdelt_collection_status=result.gdelt_status,
    )
    language = LanguageManager("fr_FR")
    page = MacroPage(language)
    page.set_snapshot(projection)
    page.show()
    app.processEvents()

    assert "READY" in page.tavily_status.text()
    assert "1/900" in page.quota_status.text()
    assert page.intelligence_table.rowCount() == 3
    assert page.news_refresh_button.text() == "Actualiser l’analyse marché"
    assert "Tavily : 1" in page.intelligence_summary.text()
    assert page.tavily_highlights.count() == 1
    assert "Market event tavily-news" in page.tavily_highlights.item(0).text()
    assert "2026-11-11 11:50 UTC" in page.tavily_highlights.item(0).text()
    assert "1 résultat(s) récent(s)" in page.tavily_highlights_label.text()
    assert page.context_table.rowCount() == 2
    assert "3 titre" in page.context_summary.text()
    assert "Tavily 1" in page.ai_source_breakdown.text()

    page.close()
    language.close()
