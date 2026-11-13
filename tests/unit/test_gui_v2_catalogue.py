from datetime import UTC, datetime

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.app.projections.catalogue import build_catalogue_projection
from trading_ig_assistant.app.qt_catalogue_controller import CatalogueSearchController
from trading_ig_assistant.app.runtime.ig_session_runtime import ActiveIGConnection
from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
from trading_ig_assistant.domain.instruments import Account, MarketDetails, MarketSummary
from trading_ig_assistant.domain.market_data import Quote
from trading_ig_assistant.domain.products import AssetClass, ProductType, TradableProduct
from trading_ig_assistant.services.product_discovery_service import (
    ProductDiscoveryResult,
    write_discovery_report,
)


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class FakeSearchAdapter:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.details_calls: list[str] = []

    def search_markets(self, query: str) -> list[MarketSummary]:
        self.queries.append(query)
        return [
            MarketSummary(
                epic="CS.D.CAC.CFD.IP",
                instrument_name="France 40",
                instrument_type="INDICES",
                expiry="DFB",
                market_status="TRADEABLE",
                raw={"bid": 8120.5, "offer": 8121.5, "percentageChange": 0.4},
            )
        ]

    def get_market_details(self, epic: str) -> MarketDetails:
        self.details_calls.append(epic)
        return MarketDetails(
            epic=epic,
            instrument_name="France 40",
            raw={
                "instrument": {
                    "currencies": [{"code": "EUR"}],
                    "lotSize": 1,
                    "accountType": "BARRIERS",
                },
                "dealingRules": {"minDealSize": 0.5},
            },
        )


def _connected_runtime(adapter: FakeSearchAdapter) -> TradingRuntime:
    runtime = TradingRuntime()
    runtime.replace_ig_connection_for_legacy_migration(
        ActiveIGConnection(
            environment=IGEnvironment.DEMO,
            current_account_id="DEMO-A",
            accounts=[Account(account_id="DEMO-A", account_name="Demo")],
            adapter=adapter,
        )
    )
    return runtime


def _wait(controller: CatalogueSearchController) -> None:
    loop = QtCore.QEventLoop()
    controller.busy_changed.connect(lambda busy: loop.quit() if not busy else None)
    QtCore.QTimer.singleShot(3000, loop.quit)
    loop.exec()
    assert controller.busy is False


def _wait_details(controller: CatalogueSearchController) -> None:
    loop = QtCore.QEventLoop()
    controller.details_busy_changed.connect(lambda busy: loop.quit() if not busy else None)
    QtCore.QTimer.singleShot(3000, loop.quit)
    loop.exec()
    assert controller.details_busy is False


def test_catalogue_search_is_explicit_bounded_and_published() -> None:
    app = _application()
    adapter = FakeSearchAdapter()
    runtime = _connected_runtime(adapter)
    controller = CatalogueSearchController(runtime)

    assert adapter.queries == []
    controller.search("France 40")
    _wait(controller)
    app.processEvents()

    snapshot = runtime.read_catalogue()
    assert adapter.queries == ["France 40"]
    assert snapshot.query == "France 40"
    assert len(snapshot.rows) == 1
    assert snapshot.rows[0].epic == "CS.D.CAC.CFD.IP"
    assert snapshot.rows[0].bid is not None


def test_catalogue_search_requires_connection_and_valid_query() -> None:
    _application()
    controller = CatalogueSearchController(TradingRuntime())
    errors: list[str] = []
    controller.error.connect(errors.append)

    controller.search("France 40")
    assert errors == ["catalogue.not_connected"]

    adapter = FakeSearchAdapter()
    controller = CatalogueSearchController(_connected_runtime(adapter))
    errors = []
    controller.error.connect(errors.append)
    controller.search("x")
    assert errors == ["catalogue.invalid_query"]
    assert adapter.queries == []


def test_selected_product_details_enrich_metadata_without_replacing_live_quote() -> None:
    app = _application()
    adapter = FakeSearchAdapter()
    runtime = _connected_runtime(adapter)
    controller = CatalogueSearchController(runtime)
    controller.search("France 40")
    _wait(controller)
    runtime.publish_live_catalogue_quote(
        generation_id=runtime.generation_id,
        quote=Quote(
            epic="CS.D.CAC.CFD.IP",
            bid=8130.0,
            offer=8131.0,
            market_state="TRADEABLE",
            raw={"DELAY": "0"},
        ),
        received_at_utc=datetime.now(UTC),
    )

    controller.resolve_product_details(runtime.read_catalogue().rows[0])
    _wait_details(controller)
    app.processEvents()

    row = runtime.read_catalogue().rows[0]
    assert adapter.details_calls == ["CS.D.CAC.CFD.IP"]
    assert row.currency == "EUR"
    assert row.product_type == "cash_or_dfb"
    assert row.min_size is not None and str(row.min_size) == "0.5"
    assert row.metadata_source == "ig-rest-market-details"
    assert row.bid is not None and str(row.bid) == "8130.0"
    assert row.provenance.source == "ig-lightstreamer"


def test_scanner_page_imports_independently_and_fits_1366_width() -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.scanner_page import ScannerPage

    app = _application()
    language = LanguageManager("fr_FR")
    page = ScannerPage(language)
    page.resize(1100, 600)
    page.show()
    app.processEvents()
    page.set_stream_scope_active(True)

    assert page.minimumSizeHint().width() <= 1100
    assert page.tabs.count() == 5
    assert page.model.rowCount() == 0
    assert len(page._market_panels) == 4
    page.close()
    language.close()


def test_scanner_releases_visible_scope_while_hidden() -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.scanner_page import ScannerPage

    app = _application()
    language = LanguageManager("fr_FR")
    page = ScannerPage(language)
    requested: list[tuple[tuple[str, ...], int]] = []
    page.stream_scope_changed.connect(
        lambda epics, total: requested.append((tuple(epics), total))
    )
    now = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
    runtime = TradingRuntime(now_provider=lambda: now)
    runtime.publish_catalogue(
        build_catalogue_projection(
            generation_id=runtime.generation_id,
            query="",
            products=(
                TradableProduct(
                    epic="CS.D.CAC.CFD.IP",
                    name="France 40",
                    product_type=ProductType.CASH_OR_DFB,
                    asset_class=AssetClass.INDICES,
                ),
                TradableProduct(
                    epic="CS.D.DAX.CFD.IP",
                    name="Germany 40",
                    product_type=ProductType.CASH_OR_DFB,
                    asset_class=AssetClass.INDICES,
                ),
            ),
            generated_at_utc=now,
            kind="inventory",
        )
    )

    page.set_snapshot(runtime.read_catalogue())
    app.processEvents()
    assert requested == []

    page.set_stream_scope_active(True)
    page._emit_stream_scope()
    assert requested[-1][0] == ("CS.D.CAC.CFD.IP", "CS.D.DAX.CFD.IP")

    page.set_stream_scope_active(False)
    assert requested[-1] == ((), 2)
    before = len(requested)
    page.set_snapshot(runtime.read_catalogue())
    app.processEvents()
    assert len(requested) == before

    page.close()
    language.close()


def test_scanner_scope_publication_is_not_starved_by_catalogue_ticks() -> None:
    """Frequent followed-product ticks must not postpone the visible 40-row scope forever."""

    from PyQt5 import QtTest

    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.scanner_page import ScannerPage

    app = _application()
    language = LanguageManager("fr_FR")
    page = ScannerPage(language)
    now = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
    snapshot = build_catalogue_projection(
        generation_id=0,
        query="",
        products=tuple(
            TradableProduct(
                epic=f"LIVE.TEST.{index}",
                name=f"Test market {index}",
                product_type=ProductType.CASH_OR_DFB,
                asset_class=AssetClass.INDICES,
            )
            for index in range(50)
        ),
        generated_at_utc=now,
        kind="inventory",
    )
    requested: list[tuple[tuple[str, ...], int]] = []
    page.stream_scope_changed.connect(
        lambda epics, total: requested.append((tuple(epics), total))
    )
    page.set_stream_scope_active(True)
    for _index in range(8):
        page.set_snapshot(snapshot)
        QtTest.QTest.qWait(50)
        app.processEvents()

    assert requested
    assert len(requested[0][0]) == 40
    assert requested[0][1] == 50

    page.close()
    language.close()


def test_runtime_scanner_keeps_configured_markets_and_merges_reference_quote() -> None:
    now = datetime(2026, 11, 9, 15, 0, tzinfo=UTC)
    runtime = TradingRuntime(now_provider=lambda: now)
    runtime.publish_catalogue(
        build_catalogue_projection(
            generation_id=runtime.generation_id,
            query="",
            products=(
                TradableProduct(
                    epic="IX.D.NASDAQ.IFD.IP",
                    name="US Tech 100",
                    product_type=ProductType.CASH_OR_DFB,
                    asset_class=AssetClass.INDICES,
                    bid=25000.0,
                    offer=25002.0,
                ),
            ),
            generated_at_utc=now,
            kind="inventory",
        )
    )

    scanner = runtime.read_scanner()
    assert len(scanner.rows) == 5
    assert scanner.rows[0].underlying_id == "US_TECH_100"
    assert scanner.rows[0].technical_score is None
    assert scanner.rows[0].reason_codes == ("SESSION_OHLC_WARMING_UP",)

    runtime.publish_live_catalogue_quote(
        generation_id=runtime.generation_id,
        quote=Quote(
            epic="IX.D.NASDAQ.IFD.IP",
            bid=25010.0,
            offer=25012.0,
            net_change=198.5,
            percent_change=0.8,
        ),
        received_at_utc=now,
    )
    row = runtime.read_scanner().rows[0]
    assert row.bid is not None and str(row.bid) == "25010.0"
    assert row.net_change is not None and str(row.net_change) == "198.5"
    assert row.quote_provenance.source == "ig-lightstreamer"


def test_scanner_opportunity_tabs_show_honest_warming_up_rows() -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.scanner_page import ScannerPage

    app = _application()
    runtime = TradingRuntime(now_provider=lambda: datetime(2026, 11, 9, 15, 0, tzinfo=UTC))
    language = LanguageManager("fr_FR")
    page = ScannerPage(language)
    page.set_scanner_snapshot(runtime.read_scanner())
    page.tabs.setCurrentIndex(1)
    page.show()
    app.processEvents()

    opportunities = page._market_panels[0]
    assert opportunities.proxy.rowCount() == 5
    assert "INCONNU" in opportunities.status.text()
    assert opportunities.model.data(opportunities.model.index(0, 5)) == "INCONNU"
    assert opportunities.model.data(opportunities.model.index(0, 8)) == "INDISPONIBLE"
    assert page._market_panels[1].proxy.rowCount() == 0
    assert page._market_panels[3].proxy.rowCount() == 5

    page.close()
    language.close()


def test_scanner_context_column_explains_level_reasons_and_provenance() -> None:
    from dataclasses import replace
    from decimal import Decimal

    from PyQt5 import QtCore

    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.models.scanner_market_table_model import (
        ScannerMarketTableModel,
    )

    language = LanguageManager("fr_FR")
    runtime = TradingRuntime(now_provider=lambda: datetime(2026, 11, 9, 15, 0, tzinfo=UTC))
    row = replace(
        runtime.read_scanner().rows[0],
        context_score=Decimal("50"),
        context_level="caution",
        context_components=("index:bullish", "event:medium", "ai:bullish"),
        context_reason_codes=("PRODUCT_EVENT_YELLOW", "PRODUCT_AI_YELLOW"),
        context_provenance=("official-news:test", "openai:test"),
        context_safety_veto=False,
    )
    model = ScannerMarketTableModel(language)
    model.set_rows((row,))
    context_index = model.index(0, 6)

    assert model.data(context_index) == "PRUDENCE · 50/100"
    tooltip = str(model.data(context_index, QtCore.Qt.ToolTipRole))
    assert "ni recommandation, ni probabilité" in tooltip
    assert "index:bullish" in tooltip
    assert "PRODUCT_AI_YELLOW" in tooltip
    assert "official-news:test" in tooltip
    assert model.data(context_index, QtCore.Qt.ForegroundRole).name() == "#f59e0b"

    language.close()


def test_watchlist_uses_reference_selection_and_session_chart_updates() -> None:
    from trading_ig_assistant.domain.market_data import ChartCandleUpdate
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.watchlist_page import WatchlistPage

    app = _application()
    runtime = TradingRuntime(now_provider=lambda: datetime(2026, 11, 9, 15, 0, tzinfo=UTC))
    runtime.publish_catalogue(
        build_catalogue_projection(
            generation_id=runtime.generation_id,
            query="",
            products=(
                TradableProduct(
                    epic="IX.D.NASDAQ.IFD.IP",
                    name="US Tech 100",
                    product_type=ProductType.CASH_OR_DFB,
                    asset_class=AssetClass.INDICES,
                ),
            ),
            generated_at_utc=datetime(2026, 11, 9, 15, 0, tzinfo=UTC),
            kind="inventory",
        )
    )
    runtime.publish_live_catalogue_quote(
        generation_id=runtime.generation_id,
        quote=Quote(
            epic="IX.D.NASDAQ.IFD.IP",
            bid=25010.0,
            offer=25012.0,
            net_change=198.5,
            percent_change=0.8,
        ),
        received_at_utc=datetime(2026, 11, 9, 15, 0, tzinfo=UTC),
    )
    language = LanguageManager("fr_FR")
    page = WatchlistPage(language)
    page.set_scanner_snapshot(runtime.read_scanner())
    page.apply_chart_update(
        ChartCandleUpdate(
            epic="IX.D.NASDAQ.IFD.IP",
            interval="1MINUTE",
            timestamp_ms=1_794_236_400_000,
            open=25000.0,
            high=25020.0,
            low=24990.0,
            close=25010.0,
        )
    )
    page.show()
    app.processEvents()

    assert page.market_list.count() == 5
    assert page.market_list.currentItem().data(QtCore.Qt.UserRole) == "IX.D.NASDAQ.IFD.IP"
    assert page.chart.display_bar_count() == 1
    assert "LIVE" in page.chart.stream_status_label.text()
    assert page.chart.change_label.text() == "Variation: +198.5"
    assert page.chart.percent_change_label.text() == "% Variation: +0.8"
    assert page.chart._plot.backgroundBrush().color().name().lower() == "#0c1627"
    assert "Source IG DEMO" in page.chart.data_context_label.text()
    assert "IX.D.NASDAQ.IFD.IP" in page.chart.data_context_label.text()
    assert "Bougies M1 observées : 1" in page.history_summary.text()

    page.close()
    language.close()


def test_watchlist_projects_explainable_scanner_signals_without_ai_call() -> None:
    from dataclasses import replace
    from decimal import Decimal

    from trading_ig_assistant.app.projections.scanner import (
        ScannerIndicatorVM,
        ScannerSignalVM,
    )
    from trading_ig_assistant.domain.market_data import ChartCandleUpdate
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.watchlist_page import WatchlistPage

    app = _application()
    now = datetime(2026, 11, 9, 15, 0, tzinfo=UTC)
    runtime = TradingRuntime(now_provider=lambda: now)
    snapshot = runtime.read_scanner()
    signal = ScannerSignalVM(
        signal_id="trend-france-40",
        product_epic="IX.D.CAC.IMF.IP",
        strategy_id="trend_follow",
        side="buy",
        data_state="ready",
        entry_low=Decimal("8280"),
        entry_high=Decimal("8282"),
        invalidation=Decimal("8272"),
        target=Decimal("8298"),
        confidence=Decimal("0.7"),
        data_quality=Decimal("0.9"),
        features=(
            ("fast_ema", Decimal("8281.5")),
            ("slow_ema", Decimal("8278.0")),
            ("atr", Decimal("7.25")),
            ("rsi", Decimal("54.5")),
            ("macd", Decimal("1.25")),
        ),
        reason_codes=("TREND_CONFIRMED",),
        provenance=(
            "chart:STREAM",
            "timeframe:M1",
            "price_basis:bid",
            "config:fast_ema_period=9",
            "config:slow_ema_period=21",
            "config:rsi_period=14",
            "config:atr_period=14",
            "config:macd_fast_period=3",
            "config:macd_slow_period=5",
            "config:macd_signal_period=2",
        ),
        generated_at_utc=now,
        valid_until_utc=now.replace(minute=10),
    )
    breakout = replace(
        signal,
        signal_id="breakout-france-40",
        strategy_id="breakout",
        side="flat",
        entry_low=None,
        entry_high=None,
        invalidation=None,
        target=None,
        features=(
            ("support", Decimal("8274")),
            ("resistance", Decimal("8286.5")),
            ("atr", Decimal("7.25")),
        ),
        reason_codes=("NO_CONFIRMED_BREAKOUT",),
    )
    france = replace(
        snapshot.rows[1],
        technical_score=Decimal("72"),
        context_score=Decimal("50"),
        context_level="caution",
        context_components=("index:bullish", "event:medium", "ai:bullish"),
        context_reason_codes=("PRODUCT_EVENT_YELLOW",),
        context_provenance=("official-news:test",),
        signal_direction="bullish",
        recommendation="watch",
        observed_candles=30,
        reason_codes=("MACRO_UNKNOWN",),
        evaluated_at_utc=now,
        strategy_signals=(breakout, signal),
        indicators=(
            ScannerIndicatorVM(
                indicator_id="ema:period:9:value",
                name="ema",
                component=None,
                state="ready",
                value=Decimal("8281.5"),
                required_points=9,
                observed_points=30,
                parameters=("period:9",),
                reason_codes=(),
                provenance=(
                    "timeframe:M1",
                    "source:chart:STREAM",
                    "price_basis:bid",
                    "period:9",
                ),
            ),
            ScannerIndicatorVM(
                indicator_id="recent_levels:period:20:support",
                name="recent_levels",
                component="support",
                state="ready",
                value=Decimal("8274"),
                required_points=20,
                observed_points=30,
                parameters=("period:20",),
                reason_codes=(),
                provenance=(
                    "timeframe:M1",
                    "source:chart:STREAM",
                    "price_basis:bid",
                    "period:20",
                ),
            ),
        ),
    )
    snapshot = replace(snapshot, rows=(snapshot.rows[0], france, *snapshot.rows[2:]))
    language = LanguageManager("fr_FR")
    page = WatchlistPage(language, "DEMO")
    page.set_scanner_snapshot(snapshot)
    page.chart.resolution_combo.setCurrentIndex(
        page.chart.resolution_combo.findData(60)
    )
    first_timestamp_ms = int(now.timestamp() * 1000) - (30 * 60_000)
    for index in range(30):
        close = 8270.0 + index
        page.apply_chart_update(
            ChartCandleUpdate(
                epic=france.reference_epic,
                interval="1MINUTE",
                timestamp_ms=first_timestamp_ms + (index * 60_000),
                open=close - 0.5,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
            )
        )
    page.select_reference_epic(france.reference_epic)
    app.processEvents()

    assert page.technical_table.rowCount() == 2
    assert page.indicator_table.rowCount() == 2
    assert page.indicator_table.item(0, 0).text() == "EMA"
    assert page.indicator_table.item(0, 1).text() == "8281.5"
    assert page.indicator_table.item(0, 3).text() == "PRÊT"
    assert page.indicator_table.item(0, 4).text() == "30/9"
    assert "M1" in page.indicator_table.item(0, 5).text()
    assert page.indicator_table.item(1, 0).text() == "Niveaux récents · Support"
    assert page.technical_table.item(0, 0).text() == "breakout"
    assert page.technical_table.item(0, 2).text() == "FLAT"
    assert page.technical_table.currentRow() == 1
    assert page.entry_overlay_check.isEnabled() is True
    assert page.signal_overlay_combo.currentText() == "trend_follow · BUY · PRÊT"
    assert "stratégie projetée" in page.signal_overlay_combo.toolTip()
    page.signal_overlay_combo.setCurrentIndex(0)
    assert page.technical_table.currentRow() == 0
    assert page.entry_overlay_check.isEnabled() is False
    assert tuple(level.label for level in page.chart._analysis_levels) == (
        "Sup.",
        "Rés.",
    )
    assert "ATR 14 : 7.25" in page.indicator_snapshot_label.text()
    assert "Support : 8274" in page.indicator_snapshot_label.text()
    assert page.ema_overlay_check.isChecked() is False
    assert page.structure_overlay_check.isChecked() is True
    page.signal_overlay_combo.setCurrentIndex(1)
    assert page.technical_table.currentRow() == 1
    assert page.technical_table.item(1, 0).text() == "trend_follow"
    assert page.technical_table.item(1, 2).text() == "BUY"
    assert "Technique 72" in page.technical_summary.text()
    assert "Contexte PRUDENCE · 50/100" in page.technical_summary.text()
    assert "index:bullish" in page.technical_summary.toolTip()
    assert "official-news:test" in page.technical_summary.toolTip()
    assert "fast_ema" in page.technical_detail.toPlainText()
    assert "EMA rapide 9 : 8281.5" in page.indicator_snapshot_label.text()
    assert "EMA lente 21 : 8278" in page.indicator_snapshot_label.text()
    assert "RSI 14 : 54.5" in page.indicator_snapshot_label.text()
    assert "IX.D.CAC.IMF.IP" in page.long_plan_text.text()
    assert "aucun signal READY" in page.short_plan_text.text()
    assert "MACRO_UNKNOWN" in page.no_trade_text.text()
    assert "niveaux attestés trend-france-40" in page.chart.data_context_label.text()
    assert tuple(level.label for level in page.chart._analysis_levels) == (
        "Entrée−",
        "Entrée+",
        "Inv.",
        "Obj.",
    )
    assert tuple(level.label_position for level in page.chart._analysis_levels) == (
        0.62,
        0.70,
        0.78,
        0.86,
    )
    assert tuple(series.label for series in page.chart._analysis_series) == (
        "EMA R",
        "EMA L",
    )
    assert tuple(len(series.points) for series in page.chart._analysis_series) == (21, 9)
    assert len(page.chart._analysis_curve_items) == 2
    assert page.indicator_panel_combo.isEnabled() is True
    assert page.indicator_panel_combo.currentData() == "atr"
    assert page.indicator_panel_combo.currentText() == "ATR 14"
    assert page.chart._indicator_panel is not None
    assert page.chart._indicator_panel.label == "ATR 14"
    assert len(page.chart._indicator_panel.series[0].points) == 16
    assert page.chart._indicator_panel.minimum == 0.0
    assert page.chart._indicator_panel.maximum > 0.0
    page.indicator_panel_combo.setCurrentIndex(
        page.indicator_panel_combo.findData("none")
    )
    assert page.indicator_panel_combo.currentData() == "none"
    assert page.chart._indicator_panel is None
    page.signal_overlay_combo.setCurrentIndex(0)
    page.signal_overlay_combo.setCurrentIndex(1)
    assert page.indicator_panel_combo.currentData() == "none"
    assert page.chart._indicator_panel is None
    page.indicator_panel_combo.setCurrentIndex(
        page.indicator_panel_combo.findData("rsi")
    )
    assert page.indicator_panel_combo.currentData() == "rsi"
    assert page.indicator_panel_combo.currentText() == "RSI 14"
    assert page.chart._indicator_panel is not None
    assert page.chart._indicator_panel.label == "RSI 14"
    assert len(page.chart._indicator_panel.series[0].points) == 15
    assert len(page.chart._indicator_curve_items) == 1
    assert page.chart._indicator_plot.isHidden() is False
    assert page.chart._indicator_legend.isVisible() is False
    page.signal_overlay_combo.setCurrentIndex(0)
    page.signal_overlay_combo.setCurrentIndex(1)
    assert page.indicator_panel_combo.currentData() == "rsi"
    page.indicator_panel_combo.setCurrentIndex(
        page.indicator_panel_combo.findData("macd")
    )
    assert page.indicator_panel_combo.currentText() == "MACD 3/5/2"
    assert page.chart._indicator_panel is not None
    assert page.chart._indicator_panel.label == "MACD 3/5/2"
    assert len(page.chart._indicator_panel.series) == 3
    assert len(page.chart._indicator_curve_items) == 3
    assert page.chart._indicator_legend.isVisible() is True
    assert page.chart._indicator_panel.minimum < 0 < page.chart._indicator_panel.maximum
    page.indicator_panel_combo.setCurrentIndex(
        page.indicator_panel_combo.findData("rsi")
    )
    refreshed_signal = replace(
        signal,
        signal_id="trend-france-40-next-candle",
        generated_at_utc=now.replace(minute=1),
    )
    refreshed_breakout = replace(
        breakout,
        signal_id="breakout-france-40-next-candle",
        generated_at_utc=now.replace(minute=1),
    )
    refreshed_france = replace(
        france,
        strategy_signals=(refreshed_breakout, refreshed_signal),
        evaluated_at_utc=now.replace(minute=1),
    )
    page.set_scanner_snapshot(
        replace(
            snapshot,
            generation_id=snapshot.generation_id + 1,
            rows=(snapshot.rows[0], refreshed_france, *snapshot.rows[2:]),
        )
    )
    app.processEvents()
    assert page.technical_table.currentRow() == 1
    assert page.signal_overlay_combo.currentText() == "trend_follow · BUY · PRÊT"
    assert page.indicator_panel_combo.currentData() == "rsi"
    assert page._selected_signal is not None
    assert page._selected_signal.signal_id == "trend-france-40-next-candle"
    page.invalidation_overlay_check.setChecked(False)
    assert tuple(level.label for level in page.chart._analysis_levels) == (
        "Entrée−",
        "Entrée+",
        "Obj.",
    )
    language.set_locale("en_US")
    page.retranslate_ui()
    assert page.overlay_title.text() == "Displayed signal:"
    assert page.technical_table.currentRow() == 1
    assert page.signal_overlay_combo.currentText() == "trend_follow · BUY · READY"
    assert "strategy projected" in page.signal_overlay_combo.toolTip()
    assert tuple(level.label for level in page.chart._analysis_levels) == (
        "Entry−",
        "Entry+",
        "Tgt.",
    )
    assert tuple(series.label for series in page.chart._analysis_series) == (
        "EMA F",
        "EMA S",
    )
    assert page.indicator_panel_label.text() == "Lower panel:"
    assert page.indicator_panel_combo.currentText() == "RSI 14"
    assert "UNKNOWN" in page.ai_status.text()
    emitted: list[bool] = []
    page.macro_open_requested.connect(lambda: emitted.append(True))
    page.ai_open_button.click()
    assert emitted == [True]

    page.close()
    language.close()


def test_watchlist_projects_advisory_ai_context_with_scope_and_ttl_guards() -> None:
    from dataclasses import replace
    from decimal import Decimal

    from trading_ig_assistant.app.projections.common import Availability
    from trading_ig_assistant.app.projections.macro import AIEvidenceRowVM
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.watchlist_page import WatchlistPage

    app = _application()
    now = datetime(2026, 11, 9, 15, 0, tzinfo=UTC)
    runtime = TradingRuntime(now_provider=lambda: now)
    scanner = runtime.read_scanner()
    macro = replace(
        runtime.read_macro(),
        ai_status=Availability.READY,
        ai_model_id="gpt-test",
        ai_prompt_version="market-context-v1",
        ai_scope="GLOBAL-MARKET-CONTEXT",
        ai_summary="Contexte contrasté : attendre une confirmation technique.",
        ai_directional_bias="unknown",
        ai_event_risk="medium",
        ai_confidence=Decimal("0.42"),
        ai_risk_flags=("SOURCE_DIVERSITY_LIMITED",),
        ai_source_signal_ids=("news:1",),
        ai_generated_at_utc=now,
        ai_valid_until_utc=now.replace(minute=10),
        ai_reason_codes=(),
        ai_evidence_rows=(
            AIEvidenceRowVM(
                signal_id="news:1",
                headline="Central bank communication remains cautious",
                source="Official source",
                source_url="https://example.test/news/1",
                excerpt="Policy guidance remains conditional.",
                content_origin="official",
                published_at_utc=now,
            ),
        ),
    )
    language = LanguageManager("fr_FR")
    page = WatchlistPage(language, "DEMO")
    page.set_scanner_snapshot(scanner)
    page.select_reference_epic(scanner.rows[1].reference_epic)
    page.set_macro_snapshot(macro)
    app.processEvents()

    assert "analyse consultative (contexte global de marché)" in page.ai_status.text()
    assert "Biais : UNKNOWN" in page.ai_status.text()
    assert "risque événementiel : MEDIUM" in page.ai_status.text()
    assert "indice interne non calibré : 42.0%" in page.ai_status.text()
    assert "ni un ordre ni une probabilité" in page.ai_status.text()
    assert "Official source" in page.ai_sources.text()
    assert "Central bank communication remains cautious" in page.ai_sources.text()

    page.set_macro_snapshot(replace(macro, ai_scope="IX.D.DAX.IFD.IP"))
    assert "hors périmètre" in page.ai_status.text()
    assert "Aucun biais propre" in page.ai_sources.text()

    page.set_macro_snapshot(replace(macro, ai_status=Availability.STALE))
    assert "analyse consultative périmée" in page.ai_status.text()

    page.close()
    language.close()


def test_watchlist_updates_quotes_incrementally_and_coalesces_chart_renders() -> None:
    from unittest import mock

    from PyQt5 import QtTest

    from trading_ig_assistant.domain.market_data import ChartCandleUpdate
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.watchlist_page import WatchlistPage

    app = _application()
    runtime = TradingRuntime(now_provider=lambda: datetime(2026, 11, 9, 15, 0, tzinfo=UTC))
    language = LanguageManager("fr_FR")
    page = WatchlistPage(language)
    snapshot = runtime.read_scanner()
    page.set_scanner_snapshot(snapshot)
    page.show()
    app.processEvents()

    with (
        mock.patch.object(
            page.chart,
            "set_chart_updates",
            wraps=page.chart.set_chart_updates,
        ) as rebuild,
        mock.patch.object(
            page.chart,
            "apply_chart_update",
            wraps=page.chart.apply_chart_update,
        ) as incremental,
    ):
        for _ in range(100):
            page.set_scanner_snapshot(snapshot)
        assert rebuild.call_count == 0

        for close in range(100):
            page.apply_chart_update(
                ChartCandleUpdate(
                    epic="IX.D.NASDAQ.IFD.IP",
                    interval="1MINUTE",
                    timestamp_ms=1_794_236_400_000,
                    open=25000.0,
                    high=25100.0,
                    low=24900.0,
                    close=25000.0 + close,
                )
            )
        QtTest.QTest.qWait(300)
        assert incremental.call_count == 1

    page.close()
    language.close()


def test_catalogue_adds_and_watchlist_removes_only_exact_current_products() -> None:
    from trading_ig_assistant.app.config import AppConfig
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.scanner_page import ScannerPage
    from trading_ig_assistant.ui.pages.watchlist_page import WatchlistPage
    from trading_ig_assistant.ui.shell.page_router import PageRouter

    app = _application()
    now = datetime(2026, 11, 10, 14, 0, tzinfo=UTC)
    snapshot = build_catalogue_projection(
        generation_id=0,
        query="",
        products=(
            TradableProduct(
                epic="LIVE.FRANCE.BARRIER.BUY",
                name="France 40 Barrières Achat",
                product_type=ProductType.BARRIER,
                asset_class=AssetClass.INDICES,
                bid=8300.0,
                offer=8302.0,
            ),
            TradableProduct(
                epic="LIVE.US.TECH.BARRIER.BUY",
                name="US Tech 100 Barrières Achat",
                product_type=ProductType.BARRIER,
                asset_class=AssetClass.INDICES,
            ),
        ),
        generated_at_utc=now,
        kind="inventory",
    )
    language = LanguageManager("fr_FR")
    stack = QtWidgets.QStackedWidget()
    router = PageRouter(stack, language, AppConfig())
    changes: list[tuple[str, ...]] = []
    router.followed_product_epics_changed.connect(changes.append)
    router.set_catalogue_snapshot(snapshot)
    router.set_followed_product_epics(())
    router.open_page("watchlist")

    watchlist = router._pages["watchlist"]
    assert isinstance(watchlist, WatchlistPage)
    assert watchlist.market_list.count() == 0

    router.open_page("scanner")
    scanner = router._pages["scanner"]
    assert isinstance(scanner, ScannerPage)
    source_row = scanner.model.row_for_epic("LIVE.FRANCE.BARRIER.BUY")
    assert source_row is not None
    proxy_index = scanner.proxy.mapFromSource(scanner.model.index(source_row, 0))
    scanner.table.selectRow(proxy_index.row())
    app.processEvents()
    scanner.follow_button.click()
    app.processEvents()

    assert router.current_key == "watchlist"
    assert changes == [("LIVE.FRANCE.BARRIER.BUY",)]
    assert watchlist.market_list.count() == 1
    assert watchlist.market_list.currentItem().data(QtCore.Qt.UserRole) == (
        "LIVE.FRANCE.BARRIER.BUY"
    )
    assert "France 40 Barrières Achat" in watchlist.chart.product_label.text()

    watchlist.remove_product_button.click()
    app.processEvents()
    assert changes[-1] == ()
    assert watchlist.market_list.count() == 0
    assert watchlist.remove_product_button.isEnabled() is False

    stack.close()
    language.close()


def test_followed_product_uses_its_direct_price_quote_and_local_m1_candle() -> None:
    from trading_ig_assistant.services.quote_candle_fallback_service import (
        QuoteCandleFallbackService,
    )
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.watchlist_page import WatchlistPage

    app = _application()
    now = datetime(2026, 11, 10, 14, 1, tzinfo=UTC)
    snapshot = build_catalogue_projection(
        generation_id=0,
        query="",
        products=(
            TradableProduct(
                epic="LIVE.FRANCE.BARRIER.BUY",
                name="France 40 Barrières Achat",
                product_type=ProductType.BARRIER,
                asset_class=AssetClass.INDICES,
                bid=8300.0,
                offer=8302.0,
            ),
        ),
        generated_at_utc=now,
        kind="inventory",
    )
    language = LanguageManager("fr_FR")
    page = WatchlistPage(language, "LIVE")
    page.set_tracked_products(snapshot.rows)
    quote = Quote(
        epic="LIVE.FRANCE.BARRIER.BUY",
        bid=8301.0,
        offer=8303.0,
        timestamp_ms=int(now.timestamp() * 1000),
    )
    update = QuoteCandleFallbackService().update(
        quote,
        observed_at_utc=now,
        environment="live",
        account_id="LIVE-A",
    )
    assert update is not None
    page.apply_chart_update(update)
    page.show()
    app.processEvents()

    assert page.market_list.count() == 1
    assert page.chart.display_bar_count() == 1
    assert "LIVE.FRANCE.BARRIER.BUY" in page.chart.data_context_label.text()
    assert "Source IG LIVE" in page.chart.data_context_label.text()

    page.close()
    language.close()


def test_catalogue_controller_loads_full_cached_inventory_without_ig_call(tmp_path) -> None:
    _application()
    cache_path = tmp_path / "product_discovery_demo.json"
    write_discovery_report(
        [
            ProductDiscoveryResult(
                search_term="all",
                candidates_count=2,
                products=[
                    TradableProduct(
                        epic="CS.D.CAC.CFD.IP",
                        name="France 40",
                        product_type=ProductType.CASH_OR_DFB,
                        asset_class=AssetClass.INDICES,
                    ),
                    TradableProduct(
                        epic="CS.D.DAX.CFD.IP",
                        name="Germany 40",
                        product_type=ProductType.CASH_OR_DFB,
                        asset_class=AssetClass.INDICES,
                    ),
                ],
            )
        ],
        cache_path,
    )
    runtime = TradingRuntime()
    controller = CatalogueSearchController(
        runtime,
        cache_path_provider=lambda _environment: cache_path,
    )

    assert controller.load_cached_inventory(IGEnvironment.DEMO) is True

    snapshot = runtime.read_catalogue()
    assert snapshot.kind == "inventory"
    assert snapshot.query is None
    assert [row.epic for row in snapshot.rows] == [
        "CS.D.CAC.CFD.IP",
        "CS.D.DAX.CFD.IP",
    ]
