from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.adapters.ig_rest import IGSession
from trading_ig_assistant.app.config import AppConfig, IGEnvironment
from trading_ig_assistant.app.projections.catalogue import build_catalogue_projection
from trading_ig_assistant.app.qt_market_stream_controller import (
    CatalogueMarketStreamController,
)
from trading_ig_assistant.app.qt_scanner_session_controller import (
    ScannerSessionController,
    _reference_analysis_registry,
)
from trading_ig_assistant.app.runtime.ig_session_runtime import ActiveIGConnection
from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
from trading_ig_assistant.domain.ai_context import (
    AIAnalysisStatus,
    MarketAIAnalysis,
    MarketContextSnapshot,
)
from trading_ig_assistant.domain.instruments import Account
from trading_ig_assistant.domain.macro_context import (
    DirectionalBias,
    EventRisk,
    MacroRibbonState,
    MarketRegime,
)
from trading_ig_assistant.domain.market_data import (
    AccountMetricsUpdate,
    ChartCandleUpdate,
    Quote,
)
from trading_ig_assistant.domain.market_navigation import IGProductMarketBinding
from trading_ig_assistant.domain.markets import CanonicalUnderlyingId
from trading_ig_assistant.domain.products import AssetClass, ProductType, TradableProduct
from trading_ig_assistant.services.market_navigation_catalog_service import (
    IGProductMarketBindingRegistry,
)
from trading_ig_assistant.services.technical_research_journal import (
    TechnicalResearchJournalError,
)


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class FakeRestAdapter:
    def __init__(self) -> None:
        self.session = IGSession(
            cst="fake-cst",
            security_token="fake-token",
            current_account_id="DEMO-A",
            lightstreamer_endpoint="https://stream.example.test",
        )


class FakeStreamAdapter:
    def __init__(self, sink: object) -> None:
        self.sink = sink
        self.started = 0
        self.subscriptions: list[list[str]] = []
        self.individual_market_subscriptions: list[list[str]] = []
        self.account_subscriptions = 0
        self.chart_subscriptions: list[tuple[list[str], str]] = []
        self.individual_chart_subscriptions: list[tuple[list[str], str]] = []
        self.stopped = 0

    def start(self) -> None:
        self.started += 1

    def subscribe_markets(self, epics: list[str]) -> None:
        self.subscriptions.append(epics)

    def subscribe_markets_individually(self, epics: list[str]) -> None:
        self.individual_market_subscriptions.append(epics)

    def subscribe_account(self) -> None:
        self.account_subscriptions += 1

    def subscribe_charts(self, epics: list[str], scale: str = "1MINUTE") -> None:
        self.chart_subscriptions.append((epics, scale))

    def subscribe_charts_individually(
        self, epics: list[str], scale: str = "1MINUTE"
    ) -> None:
        self.individual_chart_subscriptions.append((epics, scale))

    def stop(self) -> None:
        self.stopped += 1


def _runtime_with_catalogue(
    extra_products: int = 0,
    *,
    include_priority: bool = False,
) -> TradingRuntime:
    now = datetime(2026, 11, 9, 14, 0, tzinfo=UTC)
    runtime = TradingRuntime(now_provider=lambda: now)
    runtime.replace_ig_connection_for_legacy_migration(
        ActiveIGConnection(
            environment=IGEnvironment.DEMO,
            current_account_id="DEMO-A",
            accounts=[Account(account_id="DEMO-A", account_name="Demo")],
            adapter=FakeRestAdapter(),
        )
    )
    runtime.publish_catalogue(
        build_catalogue_projection(
            generation_id=runtime.generation_id,
            query="France 40",
            products=(
                TradableProduct(
                    epic="CS.D.CAC.CFD.IP",
                    name="France 40",
                    product_type=ProductType.CASH_OR_DFB,
                    asset_class=AssetClass.INDICES,
                    bid=8120.0,
                    offer=8121.0,
                ),
                TradableProduct(
                    epic="CS.D.DAX.CFD.IP",
                    name="Germany 40",
                    product_type=ProductType.CASH_OR_DFB,
                    asset_class=AssetClass.INDICES,
                ),
                *tuple(
                    TradableProduct(
                        epic=f"CS.D.TEST{index}.CFD.IP",
                        name=f"Test market {index}",
                        product_type=ProductType.CASH_OR_DFB,
                        asset_class=AssetClass.INDICES,
                    )
                    for index in range(extra_products)
                ),
                *(
                    (
                        TradableProduct(
                            epic="IX.D.NASDAQ.IFD.IP",
                            name="US Tech 100",
                            product_type=ProductType.CASH_OR_DFB,
                            asset_class=AssetClass.INDICES,
                        ),
                    )
                    if include_priority
                    else ()
                ),
            ),
            generated_at_utc=now,
        )
    )
    return runtime


def test_catalogue_stream_subscribes_visible_scope_and_merges_quote() -> None:
    app = _application()
    runtime = _runtime_with_catalogue()
    adapters: list[FakeStreamAdapter] = []

    def factory(_session: IGSession, _account_id: str, sink: object) -> FakeStreamAdapter:
        adapter = FakeStreamAdapter(sink)
        adapters.append(adapter)
        return adapter

    controller = CatalogueMarketStreamController(
        runtime,
        adapter_factory=factory,
        now_provider=lambda: datetime(2026, 11, 9, 14, 1, tzinfo=UTC),
    )

    controller.sync_scope(("CS.D.CAC.CFD.IP", "CS.D.DAX.CFD.IP"), 2)
    assert len(adapters) == 1
    assert adapters[0].started == 1
    assert adapters[0].account_subscriptions == 1
    assert adapters[0].subscriptions == [["CS.D.CAC.CFD.IP", "CS.D.DAX.CFD.IP"]]
    assert runtime.read_account_header().ig_stream_status == "connecting"

    adapters[0].sink.on_stream_status("SUBSCRIBED:PRICE")
    adapters[0].sink.on_quote(
        Quote(
            epic="CS.D.CAC.CFD.IP",
            bid=8124.5,
            offer=8125.5,
            percent_change=0.8,
            market_state="TRADEABLE",
            timestamp_ms=1_794_232_860_000,
        )
    )
    app.processEvents()

    snapshot = runtime.read_catalogue()
    assert snapshot.rows[0].bid is not None
    assert str(snapshot.rows[0].bid) == "8124.5"
    assert snapshot.rows[0].provenance.source == "ig-lightstreamer"
    assert snapshot.rows[1].provenance.source == "ig-rest-search-markets"
    assert runtime.read_account_header().ig_stream_status == "live"

    controller.stop()
    assert adapters[0].stopped == 1
    assert runtime.read_account_header().ig_stream_status == "disconnected"


def test_stream_waits_for_confirmed_connection_before_starting() -> None:
    _application()
    now = datetime(2026, 11, 9, 14, 0, tzinfo=UTC)
    runtime = TradingRuntime(now_provider=lambda: now)
    runtime.publish_catalogue(
        build_catalogue_projection(
            generation_id=runtime.generation_id,
            query="France 40",
            products=(
                TradableProduct(
                    epic="CS.D.CAC.CFD.IP",
                    name="France 40",
                    product_type=ProductType.CASH_OR_DFB,
                    asset_class=AssetClass.INDICES,
                ),
            ),
            generated_at_utc=now,
        )
    )
    adapters: list[FakeStreamAdapter] = []
    controller = CatalogueMarketStreamController(
        runtime,
        adapter_factory=lambda _session, _account_id, sink: (
            adapters.append(FakeStreamAdapter(sink)) or adapters[-1]
        ),
        priority_epics=(),
    )
    runtime.replace_ig_connection_for_legacy_migration(
        ActiveIGConnection(
            environment=IGEnvironment.LIVE,
            current_account_id="LIVE-A",
            accounts=[Account(account_id="LIVE-A", account_name="Live")],
            adapter=FakeRestAdapter(),
        )
    )

    controller.track_epics(("CS.D.CAC.CFD.IP",))
    assert adapters == []

    controller.set_connection_ready(True)
    assert len(adapters) == 1
    assert adapters[0].subscriptions == [["CS.D.CAC.CFD.IP"]]


def test_inventory_refresh_does_not_expand_followed_price_scope() -> None:
    _application()
    runtime = _runtime_with_catalogue(extra_products=3)
    adapters: list[FakeStreamAdapter] = []
    controller = CatalogueMarketStreamController(
        runtime,
        adapter_factory=lambda _session, _account_id, sink: (
            adapters.append(FakeStreamAdapter(sink)) or adapters[-1]
        ),
        priority_epics=(),
    )

    controller.track_epics(("CS.D.CAC.CFD.IP",))
    controller.sync_inventory(runtime.read_catalogue())

    assert adapters[0].subscriptions == [["CS.D.CAC.CFD.IP"]]
    assert controller.subscribed_epics == ("CS.D.CAC.CFD.IP",)


def test_catalogue_stream_caps_scope_at_ig_default_and_ignores_unknown_epics() -> None:
    _application()
    runtime = _runtime_with_catalogue(extra_products=45)
    adapters: list[FakeStreamAdapter] = []
    controller = CatalogueMarketStreamController(
        runtime,
        adapter_factory=lambda _session, _account_id, sink: (
            adapters.append(FakeStreamAdapter(sink)) or adapters[-1]
        ),
    )
    requested = tuple(row.epic for row in runtime.read_catalogue().rows) + ("UNKNOWN",)

    controller.sync_scope(requested, len(requested))

    assert len(adapters) == 1
    assert len(adapters[0].subscriptions[-1]) == 39
    assert "UNKNOWN" not in adapters[0].subscriptions[-1]


def test_stream_controller_rejects_chart_scope_that_would_exceed_global_cap() -> None:
    with pytest.raises(ValueError, match="item budget"):
        CatalogueMarketStreamController(
            TradingRuntime(),
            chart_epics=tuple(f"CHART.{index}" for index in range(40)),
        )


def test_priority_reference_market_remains_subscribed_when_visible_scope_changes() -> None:
    _application()
    runtime = _runtime_with_catalogue(extra_products=1, include_priority=True)
    adapters: list[FakeStreamAdapter] = []
    controller = CatalogueMarketStreamController(
        runtime,
        adapter_factory=lambda _session, _account_id, sink: (
            adapters.append(FakeStreamAdapter(sink)) or adapters[-1]
        ),
        item_budget=3,
        priority_epics=("IX.D.NASDAQ.IFD.IP",),
    )
    coverage: list[tuple[str, int, int, int]] = []
    controller.coverage_changed.connect(
        lambda state, active, total, priority: coverage.append((state, active, total, priority))
    )

    controller.sync_scope(("CS.D.CAC.CFD.IP", "CS.D.DAX.CFD.IP"), 2)
    controller.sync_scope(("CS.D.TEST0.CFD.IP",), 1)

    assert adapters[0].subscriptions[0] == [
        "IX.D.NASDAQ.IFD.IP",
        "CS.D.CAC.CFD.IP",
        "CS.D.DAX.CFD.IP",
    ]
    assert adapters[0].subscriptions[1] == [
        "IX.D.NASDAQ.IFD.IP",
        "CS.D.TEST0.CFD.IP",
    ]
    assert coverage[-1][1:] == (2, 1, 1)


def test_open_paper_product_is_protected_ahead_of_visible_catalogue_scope() -> None:
    _application()
    runtime = _runtime_with_catalogue()
    adapters: list[FakeStreamAdapter] = []
    controller = CatalogueMarketStreamController(
        runtime,
        adapter_factory=lambda _session, _account_id, sink: (
            adapters.append(FakeStreamAdapter(sink)) or adapters[-1]
        ),
        item_budget=1,
        priority_epics=(),
    )

    controller.sync_scope(("CS.D.DAX.CFD.IP",), 1)
    controller.protect_epics(("CS.D.CAC.CFD.IP",))

    assert adapters[0].subscriptions[0] == ["CS.D.DAX.CFD.IP"]
    assert adapters[0].subscriptions[1] == ["CS.D.CAC.CFD.IP"]
    assert controller.subscribed_epics == ("CS.D.CAC.CFD.IP",)


def test_followed_product_is_prioritized_independently_from_open_simulation() -> None:
    _application()
    runtime = _runtime_with_catalogue()
    adapters: list[FakeStreamAdapter] = []
    controller = CatalogueMarketStreamController(
        runtime,
        adapter_factory=lambda _session, _account_id, sink: (
            adapters.append(FakeStreamAdapter(sink)) or adapters[-1]
        ),
        item_budget=2,
        priority_epics=(),
    )

    controller.sync_scope(("CS.D.DAX.CFD.IP",), 1)
    controller.protect_epics(("CS.D.CAC.CFD.IP",))
    controller.track_epics(("CS.D.DAX.CFD.IP",))

    assert controller.subscribed_epics == (
        "CS.D.CAC.CFD.IP",
        "CS.D.DAX.CFD.IP",
    )
    assert adapters[0].subscriptions[-1] == [
        "CS.D.CAC.CFD.IP",
        "CS.D.DAX.CFD.IP",
    ]


def test_followed_exact_product_keeps_price_stream_when_it_is_also_a_chart_reference() -> None:
    _application()
    runtime = _runtime_with_catalogue(include_priority=True)
    adapters: list[FakeStreamAdapter] = []
    controller = CatalogueMarketStreamController(
        runtime,
        adapter_factory=lambda _session, _account_id, sink: (
            adapters.append(FakeStreamAdapter(sink)) or adapters[-1]
        ),
        priority_epics=(),
        chart_epics=("IX.D.NASDAQ.IFD.IP",),
    )

    controller.track_epics(("IX.D.NASDAQ.IFD.IP",))
    controller.sync_scope(("CS.D.CAC.CFD.IP",), 1)

    assert adapters[0].chart_subscriptions[-1] == (
        ["IX.D.NASDAQ.IFD.IP"],
        "1MINUTE",
    )
    assert "IX.D.NASDAQ.IFD.IP" in adapters[0].subscriptions[-1]


def test_account_stream_tick_updates_header_and_dashboard() -> None:
    app = _application()
    runtime = _runtime_with_catalogue()
    adapters: list[FakeStreamAdapter] = []
    controller = CatalogueMarketStreamController(
        runtime,
        adapter_factory=lambda _session, _account_id, sink: (
            adapters.append(FakeStreamAdapter(sink)) or adapters[-1]
        ),
        now_provider=lambda: datetime(2026, 11, 9, 14, 2, tzinfo=UTC),
    )
    controller.sync_scope(("CS.D.CAC.CFD.IP",), 1)
    # The production connection projection supplies currency-bearing REST values.
    from trading_ig_assistant.app.projections.account_projection import (
        build_account_header_projection,
    )

    runtime.publish_account_header(
        build_account_header_projection(
            generation_id=runtime.generation_id,
            account=Account(
                account_id="DEMO-A",
                account_name="Demo",
                currency="EUR",
                balance=10000.0,
            ),
            environment="demo",
            execution_mode="PAPER",
            open_positions_count=0,
            rest_status="connected",
            stream_status="connecting",
            ai_status="not_configured",
            generated_at_utc=datetime(2026, 11, 9, 14, 0, tzinfo=UTC),
        )
    )
    adapters[0].sink.on_account_metrics(
        AccountMetricsUpdate(
            account_id="DEMO-A",
            funds=10020.0,
            available_to_deal=9270.0,
            profit_loss=20.0,
            margin=750.0,
            equity=10020.0,
        )
    )
    app.processEvents()

    header = runtime.read_account_header()
    dashboard = runtime.read_dashboard()
    assert header.equity is not None and str(header.equity.value) == "10020.0"
    assert header.equity.provenance.source == "ig-lightstreamer-account"
    assert header.available_funds is not None
    assert dashboard.equity == header.equity
    assert dashboard.account_profit_loss == header.account_profit_loss


def test_reference_chart_items_share_budget_and_feed_catalogue_quote() -> None:
    app = _application()
    runtime = _runtime_with_catalogue(include_priority=True)
    adapters: list[FakeStreamAdapter] = []
    controller = CatalogueMarketStreamController(
        runtime,
        adapter_factory=lambda _session, _account_id, sink: (
            adapters.append(FakeStreamAdapter(sink)) or adapters[-1]
        ),
        item_budget=39,
        priority_epics=("IX.D.NASDAQ.IFD.IP",),
        chart_epics=("IX.D.NASDAQ.IFD.IP",),
        now_provider=lambda: datetime(2026, 11, 9, 14, 3, tzinfo=UTC),
    )
    chart_updates: list[ChartCandleUpdate] = []
    quotes: list[Quote] = []
    controller.chart_update_received.connect(chart_updates.append)
    controller.quote_received.connect(quotes.append)

    controller.sync_scope(tuple(row.epic for row in runtime.read_catalogue().rows), 3)

    assert adapters[0].chart_subscriptions == [(["IX.D.NASDAQ.IFD.IP"], "1MINUTE")]
    assert "IX.D.NASDAQ.IFD.IP" not in adapters[0].subscriptions[-1]
    update = ChartCandleUpdate(
        epic="IX.D.NASDAQ.IFD.IP",
        interval="1MINUTE",
        timestamp_ms=1_794_233_000_000,
        close=25011.0,
        raw={
            "BID_CLOSE": "25010",
            "OFR_CLOSE": "25012",
            "DAY_NET_CHG_MID": "198.5",
            "DAY_PERC_CHG_MID": "0.8",
        },
    )
    adapters[0].sink.on_chart(update)
    app.processEvents()

    row = next(row for row in runtime.read_catalogue().rows if row.epic == "IX.D.NASDAQ.IFD.IP")
    assert str(row.bid) == "25010.0"
    assert str(row.offer) == "25012.0"
    assert str(row.net_change) == "198.5"
    assert str(row.percent_change) == "0.8"
    assert chart_updates == [update]
    assert len(quotes) == 1
    assert quotes[0].net_change == 198.5


def test_reference_chart_updates_scanner_when_live_catalogue_has_no_reference_product() -> None:
    app = _application()
    runtime = _runtime_with_catalogue()
    adapters: list[FakeStreamAdapter] = []
    controller = CatalogueMarketStreamController(
        runtime,
        adapter_factory=lambda _session, _account_id, sink: (
            adapters.append(FakeStreamAdapter(sink)) or adapters[-1]
        ),
        chart_epics=("IX.D.NASDAQ.IFD.IP",),
        now_provider=lambda: datetime(2026, 11, 10, 12, 30, tzinfo=UTC),
    )
    controller.sync_scope(tuple(row.epic for row in runtime.read_catalogue().rows), 2)

    adapters[0].sink.on_chart(
        ChartCandleUpdate(
            epic="IX.D.NASDAQ.IFD.IP",
            interval="1MINUTE",
            timestamp_ms=1_794_309_000_000,
            close=27840.0,
            raw={
                "BID_CLOSE": "27839",
                "OFR_CLOSE": "27841",
                "DAY_OPEN_MID": "27700",
            },
        )
    )
    app.processEvents()

    row = next(
        row
        for row in runtime.read_scanner().rows
        if row.reference_epic == "IX.D.NASDAQ.IFD.IP"
    )
    assert str(row.bid) == "27839.0"
    assert str(row.offer) == "27841.0"
    assert str(row.net_change) == "140.0"
    assert row.percent_change is not None
    assert round(float(row.percent_change), 4) == pytest.approx(0.5054)
    assert row.quote_provenance.reason_codes == ("LIVE_REFERENCE_CHART_QUOTE",)

    runtime.publish_live_catalogue_quote(
        generation_id=runtime.generation_id,
        quote=Quote(
            epic="CS.D.CAC.CFD.IP",
            bid=8124.0,
            offer=8125.0,
            percent_change=0.8,
        ),
        received_at_utc=datetime(2026, 11, 10, 12, 31, tzinfo=UTC),
    )
    retained = next(
        row
        for row in runtime.read_scanner().rows
        if row.reference_epic == "IX.D.NASDAQ.IFD.IP"
    )
    assert retained.bid == row.bid
    assert retained.offer == row.offer
    assert retained.net_change == row.net_change
    assert retained.percent_change == row.percent_change
    assert retained.quote_provenance == row.quote_provenance


def test_watchlist_clears_session_candles_on_environment_or_account_change() -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.watchlist_page import WatchlistPage

    app = _application()
    assert app is not None
    page = WatchlistPage(LanguageManager("fr_FR"), "DEMO")
    update = ChartCandleUpdate(
        epic="IX.D.NASDAQ.IFD.IP",
        interval="1MINUTE",
        timestamp_ms=1_794_309_000_000,
        close=27840.0,
    )
    page.apply_chart_update(update)
    assert page._chart_updates == {"IX.D.NASDAQ.IFD.IP": [update]}

    page.set_environment("LIVE")
    assert page._chart_updates == {}
    page.apply_chart_update(update)
    page.set_environment("LIVE")
    assert page._chart_updates == {}
    page.close()


def test_live_grouped_chart_permission_error_retries_each_market_once() -> None:
    app = _application()
    runtime = _runtime_with_catalogue(include_priority=True)
    adapters: list[FakeStreamAdapter] = []
    chart_epics = ("IX.D.NASDAQ.IFD.IP", "CS.D.CAC.CFD.IP")
    controller = CatalogueMarketStreamController(
        runtime,
        adapter_factory=lambda _session, _account_id, sink: (
            adapters.append(FakeStreamAdapter(sink)) or adapters[-1]
        ),
        chart_epics=chart_epics,
    )
    errors: list[str] = []
    unavailable: list[str] = []
    controller.error.connect(errors.append)
    controller.chart_market_unavailable.connect(unavailable.append)

    controller.sync_scope(tuple(row.epic for row in runtime.read_catalogue().rows), 3)
    adapters[0].sink.on_stream_error(
        "Subscription error for CHART:2-markets:1MINUTE: -1 Insufficient permissions"
    )
    app.processEvents()

    assert adapters[0].individual_chart_subscriptions == [(list(chart_epics), "1MINUTE")]
    assert errors == ["stream.chart_group_degraded"]
    assert runtime.read_account_header().ig_stream_status == "subscribing"

    controller.sync_scope(("IX.D.NASDAQ.IFD.IP",), 1)
    assert adapters[0].chart_subscriptions == [(list(chart_epics), "1MINUTE")]
    assert adapters[0].individual_chart_subscriptions == [
        (list(chart_epics), "1MINUTE"),
        (list(chart_epics), "1MINUTE"),
    ]

    adapters[0].sink.on_stream_error(
        "Subscription error for CHART:CS.D.CAC.CFD.IP:1MINUTE: -1 Insufficient permissions"
    )
    adapters[0].sink.on_stream_error(
        "Subscription error for CHART:CS.D.CAC.CFD.IP:1MINUTE: -1 Insufficient permissions"
    )
    app.processEvents()

    assert adapters[0].individual_chart_subscriptions == [
        (list(chart_epics), "1MINUTE"),
        (list(chart_epics), "1MINUTE"),
    ]
    assert errors == [
        "stream.chart_group_degraded",
        "stream.chart_market_unavailable",
    ]
    # The visible scope now contains only references; the permitted CHART item remains covered.
    assert controller._coverage_count == 1
    assert controller._unavailable_chart_epics == {"CS.D.CAC.CFD.IP"}
    assert unavailable == ["CS.D.CAC.CFD.IP"]


def test_scope_reduction_commits_before_synchronous_catalogue_notification() -> None:
    """Leaving the Scanner must not recursively reapply the previous PRICE scope."""

    _application()
    runtime = _runtime_with_catalogue(extra_products=3)
    adapters: list[FakeStreamAdapter] = []
    controller = CatalogueMarketStreamController(
        runtime,
        adapter_factory=lambda _session, _account_id, sink: (
            adapters.append(FakeStreamAdapter(sink)) or adapters[-1]
        ),
        priority_epics=(),
    )
    errors: list[str] = []
    controller.error.connect(errors.append)
    runtime.subscribe("catalogue", controller.sync_inventory)
    all_epics = tuple(row.epic for row in runtime.read_catalogue().rows)

    controller.sync_scope(all_epics, len(all_epics))
    controller.track_epics((all_epics[0],))
    controller.sync_scope((), 0)

    assert controller.subscribed_epics == (all_epics[0],)
    assert adapters[0].subscriptions[-1] == [all_epics[0]]
    assert adapters[0].stopped == 0
    assert errors == []


def test_price_permission_error_still_fails_the_catalogue_stream() -> None:
    app = _application()
    runtime = _runtime_with_catalogue(include_priority=True)
    adapters: list[FakeStreamAdapter] = []
    controller = CatalogueMarketStreamController(
        runtime,
        adapter_factory=lambda _session, _account_id, sink: (
            adapters.append(FakeStreamAdapter(sink)) or adapters[-1]
        ),
        chart_epics=("IX.D.NASDAQ.IFD.IP", "CS.D.CAC.CFD.IP"),
    )
    errors: list[str] = []
    controller.error.connect(errors.append)
    controller.sync_scope(tuple(row.epic for row in runtime.read_catalogue().rows), 3)

    adapters[0].sink.on_stream_error(
        "Subscription error for PRICE: -1 Insufficient permissions"
    )
    app.processEvents()

    assert adapters[0].individual_chart_subscriptions == []
    assert errors == ["Subscription error for PRICE: -1 Insufficient permissions"]
    assert runtime.read_account_header().ig_stream_status == "failed"


def test_price_invalid_group_isolates_only_the_rejected_market() -> None:
    app = _application()
    runtime = _runtime_with_catalogue(extra_products=3)
    adapters: list[FakeStreamAdapter] = []
    controller = CatalogueMarketStreamController(
        runtime,
        adapter_factory=lambda _session, _account_id, sink: (
            adapters.append(FakeStreamAdapter(sink)) or adapters[-1]
        ),
        priority_epics=(),
    )
    errors: list[str] = []
    controller.error.connect(errors.append)
    epics = tuple(row.epic for row in runtime.read_catalogue().rows)
    controller.sync_scope(epics, len(epics))

    adapters[0].sink.on_stream_error("Subscription error for PRICE: 21 Invalid group")
    app.processEvents()

    assert adapters[0].individual_market_subscriptions == [list(epics)]
    assert errors == ["stream.price_group_degraded"]
    assert runtime.read_account_header().ig_stream_status == "subscribing"

    rejected = epics[1]
    adapters[0].sink.on_stream_error(
        f"Subscription error for PRICE:{rejected}: 21 Invalid group"
    )
    adapters[0].sink.on_stream_error(
        f"Subscription error for PRICE:{rejected}: 21 Invalid group"
    )
    app.processEvents()

    assert controller._unavailable_price_epics == {rejected}
    assert controller._coverage_count == len(epics) - 1
    assert errors == [
        "stream.price_group_degraded",
        "stream.price_market_unavailable",
    ]
    assert runtime.read_account_header().ig_stream_status != "failed"

    controller.sync_scope(epics, len(epics))
    expected = [epic for epic in epics if epic != rejected]
    assert adapters[0].individual_market_subscriptions[-1] == expected
    assert controller.subscribed_epics == tuple(expected)


def test_scanner_session_controller_reports_real_candle_progress_only() -> None:
    _application()
    runtime = _runtime_with_catalogue(include_priority=True)
    controller = ScannerSessionController(
        runtime,
        IGProductMarketBindingRegistry(
            (
                IGProductMarketBinding(
                    product_epic="IX.D.NASDAQ.IFD.IP",
                    canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
                    reference_epic="IX.D.NASDAQ.IFD.IP",
                    provenance=("test",),
                ),
            )
        ),
        AppConfig(),
        reference_epics=("IX.D.NASDAQ.IFD.IP",),
        now_provider=lambda: datetime(2026, 11, 9, 14, 6, tzinfo=UTC),
    )

    controller.ingest_chart_update(
        ChartCandleUpdate(
            epic="IX.D.NASDAQ.IFD.IP",
            interval="1MINUTE",
            timestamp_ms=1_794_233_040_000,
            open=25000.0,
            high=25020.0,
            low=24990.0,
            close=25010.0,
            end_of_candle=True,
        )
    )

    row = runtime.read_scanner().rows[0]
    assert row.reference_epic == "IX.D.NASDAQ.IFD.IP"
    assert row.observed_candles == 0
    assert row.required_candles == 24
    assert row.reason_codes == ("SESSION_OHLC_WARMING_UP",)

    controller.ingest_chart_update(
        ChartCandleUpdate(
            epic="IX.D.NASDAQ.IFD.IP",
            interval="1MINUTE",
            timestamp_ms=1_794_233_100_000,
            open=25010.0,
            high=25030.0,
            low=25000.0,
            close=25020.0,
            end_of_candle=True,
        )
    )
    row = runtime.read_scanner().rows[0]
    assert row.observed_candles == 1
    assert row.evaluated_at_utc is None
    assert row.recommendation == "unavailable"

    runtime.publish_live_catalogue_quote(
        generation_id=runtime.generation_id,
        quote=Quote(epic="IX.D.NASDAQ.IFD.IP", bid=25021.0, offer=25023.0),
        received_at_utc=datetime(2026, 11, 9, 14, 6, tzinfo=UTC),
    )
    assert runtime.read_scanner().rows[0].observed_candles == 1


def test_scanner_session_controller_uses_latest_attested_market_context() -> None:
    now = datetime(2026, 11, 9, 14, 6, tzinfo=UTC)
    runtime = _runtime_with_catalogue(include_priority=True)
    macro = MacroRibbonState(
        schema_version=1,
        regime=MarketRegime.RISK_ON,
        index_bias=DirectionalBias.BULLISH,
        gold_bias=DirectionalBias.NEUTRAL,
        event_risk=EventRisk.MEDIUM,
        signals=(),
        generated_at_utc=now,
        reason_codes=(),
        provenance=("test:attested-macro",),
    )
    analysis = MarketAIAnalysis(
        status=AIAnalysisStatus.AVAILABLE,
        model_id="fixture",
        prompt_version="fixture-v1",
        market_scope="GLOBAL-MARKET-CONTEXT",
        directional_bias=DirectionalBias.BULLISH,
        event_risk=EventRisk.MEDIUM,
        confidence=Decimal("0.60"),
        summary="Global advisory context fixture.",
        risk_flags=(),
        source_signal_ids=("news:fixture",),
        generated_at_utc=now,
        valid_until_utc=now + timedelta(minutes=10),
    )
    snapshot = MarketContextSnapshot(
        schema_version=1,
        snapshot_id="context:fixture",
        instrument_id="GLOBAL-MARKET-CONTEXT",
        macro_state=macro,
        ai_analysis=analysis,
        generated_at_utc=now,
        valid_until_utc=now + timedelta(minutes=10),
        reason_codes=(),
        provenance=("test:context",),
    )
    assert runtime.publish_market_context(
        generation_id=runtime.generation_id,
        snapshot=snapshot,
    )
    controller = ScannerSessionController(
        runtime,
        IGProductMarketBindingRegistry(()),
        AppConfig(),
        reference_epics=("IX.D.NASDAQ.IFD.IP",),
        now_provider=lambda: now,
    )
    captured: dict[str, object] = {}
    original_scan = controller._scanner.scan

    def capturing_scan(**kwargs: object):
        captured.update(kwargs)
        return original_scan(**kwargs)

    controller._scanner.scan = capturing_scan  # type: ignore[method-assign]
    controller._run_analysis()

    assert captured["macro_state"] is macro
    assert captured["ai_snapshot"] is snapshot


def test_scanner_publication_survives_research_journal_failure() -> None:
    now = datetime(2026, 11, 9, 14, 6, tzinfo=UTC)
    runtime = _runtime_with_catalogue(include_priority=True)
    calls: list[tuple[IGEnvironment, str | None]] = []
    published: list[bool] = []
    original_publish = runtime.publish_scanner_analysis

    def capturing_publish(**kwargs):
        published.append(True)
        return original_publish(**kwargs)

    runtime.publish_scanner_analysis = capturing_publish  # type: ignore[method-assign]

    class FailingRecorder:
        def record(self, _result, *, environment, account_id):
            assert published == [True]
            calls.append((environment, account_id))
            raise TechnicalResearchJournalError("technical_journal.write_failed")

    controller = ScannerSessionController(
        runtime,
        IGProductMarketBindingRegistry(()),
        AppConfig(),
        reference_epics=("IX.D.NASDAQ.IFD.IP",),
        now_provider=lambda: now,
        research_recorder=FailingRecorder(),  # type: ignore[arg-type]
    )
    errors: list[str] = []
    controller.error.connect(errors.append)

    controller._run_analysis()

    assert published == [True]
    assert calls == [(IGEnvironment.DEMO, "DEMO-A")]
    assert errors == ["technical_journal.write_failed"]


def test_scanner_uses_exact_product_candles_after_reference_chart_denial() -> None:
    _application()
    now = datetime(2026, 11, 9, 14, 30, tzinfo=UTC)
    runtime = _runtime_with_catalogue()
    binding = IGProductMarketBinding(
        product_epic="CS.D.CAC.CFD.IP",
        canonical_underlying_id=CanonicalUnderlyingId.FRANCE_40,
        reference_epic="IX.D.CAC.IMF.IP",
        provenance=("test:explicit-product-reference",),
    )
    controller = ScannerSessionController(
        runtime,
        IGProductMarketBindingRegistry((binding,)),
        AppConfig(product_market_bindings=(binding,)),
        reference_epics=("IX.D.CAC.IMF.IP",),
        now_provider=lambda: now,
    )
    errors: list[str] = []
    controller.error.connect(errors.append)

    first = ChartCandleUpdate(
        epic="CS.D.CAC.CFD.IP",
        interval="1MINUTE",
        timestamp_ms=1_794_233_040_000,
        open=8120.0,
        high=8121.0,
        low=8119.0,
        close=8120.5,
        raw={
            "BID_OPEN": 8120.0,
            "BID_HIGH": 8121.0,
            "BID_LOW": 8119.0,
            "BID_CLOSE": 8120.5,
        },
    )
    controller.ingest_product_chart_update(first)
    france = next(
        row for row in runtime.read_scanner().rows if row.reference_epic == "IX.D.CAC.IMF.IP"
    )
    assert france.observed_candles == 0

    controller.enable_product_quote_fallback("IX.D.CAC.IMF.IP")
    for index in range(25):
        price = 8120.0 + index
        controller.ingest_product_chart_update(
            ChartCandleUpdate(
                epic="CS.D.CAC.CFD.IP",
                interval="1MINUTE",
                timestamp_ms=1_794_233_040_000 + index * 60_000,
                open=price,
                high=price + 1.0,
                low=price - 1.0,
                close=price + 0.5,
                raw={
                    "BID_OPEN": price,
                    "BID_HIGH": price + 1.0,
                    "BID_LOW": price - 1.0,
                    "BID_CLOSE": price + 0.5,
                },
            )
        )

    france = next(
        row for row in runtime.read_scanner().rows if row.reference_epic == "IX.D.CAC.IMF.IP"
    )
    assert errors == []
    assert france.observed_candles == 24
    assert france.strategy_signals
    assert {signal.product_epic for signal in france.strategy_signals} == {
        "CS.D.CAC.CFD.IP"
    }
    assert any(
        "gui-v2:exact-product-price-candle-fallback" in signal.provenance
        for signal in france.strategy_signals
    )


def test_scanner_adds_all_reference_markets_as_analysis_only_bindings() -> None:
    configured = IGProductMarketBindingRegistry(())
    reference_epics = (
        "IX.D.NASDAQ.IFD.IP",
        "IX.D.CAC.IMF.IP",
        "IX.D.DAX.IFMM.IP",
        "CS.D.CFEGOLD.CEF.IP",
        "CC.D.CL.UEF.IP",
    )

    analysis = _reference_analysis_registry(
        configured,
        reference_epics=reference_epics,
    )

    assert configured.bindings() == ()
    assert tuple(binding.product_epic for binding in analysis.bindings()) == tuple(
        sorted(reference_epics)
    )
    assert all(
        binding.product_epic == binding.reference_epic
        and binding.provenance == ("gui-v2:analysis-only-reference-market",)
        for binding in analysis.bindings()
    )


def test_scanner_filters_locally_and_emits_visible_stream_scope() -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.scanner_page import ScannerPage

    app = _application()
    language = LanguageManager("fr_FR")
    page = ScannerPage(language)
    page.set_snapshot(_runtime_with_catalogue().read_catalogue())
    requested: list[tuple[tuple[str, ...], int]] = []
    page.stream_scope_changed.connect(lambda epics, total: requested.append((tuple(epics), total)))
    page.show()
    app.processEvents()
    page.set_stream_scope_active(True)

    assert page.tabs.currentIndex() == 0
    assert page.table.columnWidth(0) == 30
    assert page.table.columnWidth(1) >= 300
    assert page.table.isSortingEnabled() is True
    assert page.proxy.rowCount() == 2
    page.query.setText("G")
    assert page.proxy.rowCount() == 1
    assert page.model.rowCount() == 2
    page._emit_stream_scope()
    assert requested[-1] == (("CS.D.DAX.CFD.IP",), 1)

    page.query.clear()
    page.table.sortByColumn(2, QtCore.Qt.DescendingOrder)
    app.processEvents()
    visible_epics = tuple(
        str(page.proxy.index(row, 0).data(QtCore.Qt.UserRole))
        for row in range(page.proxy.rowCount())
    )
    assert visible_epics == tuple(sorted(visible_epics, reverse=True))

    page.close()
    language.close()


def test_scanner_places_direct_major_markets_before_option_chains() -> None:
    from trading_ig_assistant.ui.pages.scanner_page import _prioritize_catalogue_rows

    now = datetime(2026, 11, 10, 14, 0, tzinfo=UTC)
    snapshot = build_catalogue_projection(
        generation_id=0,
        query="",
        products=(
            TradableProduct(
                epic="OP.D.OTCNAS4.20000P.IP",
                name="US Tech 100 20000 PUT ($1)",
                product_type=ProductType.OPTION,
                asset_class=AssetClass.INDICES,
            ),
            TradableProduct(
                epic="GENERIC",
                name="Generic market",
                product_type=ProductType.CASH_OR_DFB,
                asset_class=AssetClass.INDICES,
            ),
            TradableProduct(
                epic="IX.D.CAC.OPTCALL2.IP",
                name="France 40 Barrières Achat",
                product_type=ProductType.BARRIER,
                asset_class=AssetClass.INDICES,
            ),
            TradableProduct(
                epic="IX.D.NASDAQ.OPTCALL2.IP",
                name="US Tech 100 Barrières Achat",
                product_type=ProductType.BARRIER,
                asset_class=AssetClass.INDICES,
            ),
        ),
        generated_at_utc=now,
        kind="inventory",
    )

    ordered = _prioritize_catalogue_rows(snapshot.rows)

    assert tuple(row.epic for row in ordered) == (
        "IX.D.NASDAQ.OPTCALL2.IP",
        "IX.D.CAC.OPTCALL2.IP",
        "OP.D.OTCNAS4.20000P.IP",
        "GENERIC",
    )


def test_live_quote_update_keeps_model_index_and_selection_stable() -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.scanner_page import ScannerPage

    app = _application()
    language = LanguageManager("fr_FR")
    runtime = _runtime_with_catalogue()
    page = ScannerPage(language)
    page.set_snapshot(runtime.read_catalogue())
    assert page.model.data(page.model.index(0, 0), QtCore.Qt.DecorationRole).name() == "#64748b"
    page.table.selectRow(0)
    persistent = QtCore.QPersistentModelIndex(page.model.index(0, 0))
    resets: list[bool] = []
    changes: list[bool] = []
    page.model.modelReset.connect(lambda: resets.append(True))
    page.model.dataChanged.connect(lambda *_args: changes.append(True))

    runtime.publish_live_catalogue_quote(
        generation_id=runtime.generation_id,
        quote=Quote(epic="CS.D.CAC.CFD.IP", bid=8130.0, offer=8131.0),
        received_at_utc=datetime(2026, 11, 9, 14, 2, tzinfo=UTC),
    )
    page.set_snapshot(runtime.read_catalogue())
    app.processEvents()

    assert page.model.data(page.model.index(0, 0), QtCore.Qt.DecorationRole).name() == "#22c55e"
    assert persistent.isValid()
    assert page.table.selectionModel().selectedRows()[0].row() == 0
    assert resets == []
    assert changes == [True]

    page.close()
    language.close()
