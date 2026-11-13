from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from PyQt5 import QtWidgets

from trading_ig_assistant.domain.market_data import (
    Candle,
    CandleSource,
    ChartCandleSeries,
    ChartPriceBasis,
)
from trading_ig_assistant.domain.products import (
    AssetClass,
    ProductDirection,
    ProductType,
    TradableProduct,
)
from trading_ig_assistant.services.product_discovery_service import ProductDiscoveryResult
from trading_ig_assistant.services.scanner_preview_service import (
    PREVIEW_RULES_VERSION,
    build_scanner_preview,
    chart_series_to_closed_indicator_input,
)
from trading_ig_assistant.ui.main_window import MainWindow
from trading_ig_assistant.ui.scanner_view import ScannerPreviewWidget

START = datetime(2026, 11, 5, 9, 0, tzinfo=UTC)


def _series(*, trailing_close: str = "999", resolution_seconds: int = 60) -> ChartCandleSeries:
    candles = []
    for index in range(30):
        close = Decimal(index + 100)
        if index == 29:
            close = Decimal(trailing_close)
        candles.append(
            Candle(
                timestamp=START + timedelta(seconds=resolution_seconds * index),
                open=close,
                high=close + Decimal("1"),
                low=close - Decimal("1"),
                close=close,
                volume=Decimal("10"),
            )
        )
    return ChartCandleSeries(
        selected_product_epic="SYNTHETIC.EPIC",
        chart_source_epic="SYNTHETIC.CHART",
        resolution_seconds=resolution_seconds,
        price_basis=ChartPriceBasis.MID,
        candles=tuple(candles),
        sources=tuple(CandleSource.CACHE for _item in candles),
    )


def test_preview_excludes_last_chart_candle_and_is_deterministic() -> None:
    first = build_scanner_preview(_series(trailing_close="999"))
    second = build_scanner_preview(_series(trailing_close="-999"))

    assert first.used_closed_candles == 29
    assert first.excluded_trailing_candles == 1
    assert first.excluded_pre_gap_candles == 0
    assert first.signals == second.signals
    assert tuple(signal.strategy_id for signal in first.signals) == (
        "breakout",
        "pullback",
        "trend_follow",
    )
    assert all(signal.strategy_version == PREVIEW_RULES_VERSION for signal in first.signals)
    assert "NO_COMPLETE_SCANNER_SCORE" in first.limitations
    assert tuple((indicator.name, indicator.state.value) for indicator in first.indicators) == (
        ("ema", "ready"),
        ("ema", "ready"),
        ("atr", "ready"),
        ("recent_levels", "ready"),
        ("rsi", "ready"),
    )
    assert all(indicator.observed_points == 29 for indicator in first.indicators)
    assert first.indicators == second.indicators


def test_chart_conversion_rejects_unknown_resolution_and_warms_up_with_one_candle() -> None:
    with pytest.raises(ValueError, match="resolution"):
        chart_series_to_closed_indicator_input(_series(resolution_seconds=120))
    tiny = _series()
    one_candle = ChartCandleSeries(
        selected_product_epic=tiny.selected_product_epic,
        chart_source_epic=tiny.chart_source_epic,
        resolution_seconds=60,
        price_basis=tiny.price_basis,
        candles=tiny.candles[:1],
        sources=tiny.sources[:1],
    )

    indicator_input = chart_series_to_closed_indicator_input(one_candle)

    assert indicator_input.candles == ()


def test_preview_uses_only_continuous_suffix_after_cache_gap() -> None:
    complete = _series()
    candles = list(complete.candles)
    for index in range(25, len(candles)):
        candle = candles[index]
        candles[index] = type(candle)(
            timestamp=candle.timestamp + timedelta(days=2),
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
        )
    preview = build_scanner_preview(
        ChartCandleSeries(
            selected_product_epic=complete.selected_product_epic,
            chart_source_epic=complete.chart_source_epic,
            resolution_seconds=complete.resolution_seconds,
            price_basis=complete.price_basis,
            candles=tuple(candles),
            sources=complete.sources,
        )
    )

    assert preview.used_closed_candles == 4
    assert preview.excluded_pre_gap_candles == 25
    assert "DATA_GAP_EARLIER_CANDLES_EXCLUDED" in preview.limitations
    assert all(signal.data_state.value == "warming_up" for signal in preview.signals)
    assert all(signal.side.value == "flat" for signal in preview.signals)
    assert all(indicator.state.value == "warming_up" for indicator in preview.indicators)
    assert all(indicator.observed_points == 4 for indicator in preview.indicators)


def test_preview_rejects_a_stale_persisted_snapshot() -> None:
    series = _series()

    with pytest.raises(ValueError, match="STALE_HISTORY"):
        build_scanner_preview(
            series,
            as_of_utc=series.candles[-1].timestamp + timedelta(minutes=5),
        )


def test_scanner_spread_does_not_use_explicitly_delayed_quote() -> None:
    from trading_ig_assistant.domain.market_data import Quote
    from trading_ig_assistant.ui.main_window import _scanner_quote_spread

    assert _scanner_quote_spread(Quote(epic="A", bid=100, offer=102, raw={"DELAY": "1"})) is None
    assert _scanner_quote_spread(
        Quote(epic="A", bid=100, offer=102, raw={"DELAY": "0"})
    ) == Decimal("2")
    assert _scanner_quote_spread(Quote(epic="A", bid=100, offer=102)) == Decimal("2")


def test_preview_accepts_a_recent_snapshot() -> None:
    series = _series()

    preview = build_scanner_preview(
        series,
        as_of_utc=series.candles[-1].timestamp + timedelta(minutes=2),
    )

    assert preview.used_closed_candles == 29


def test_scanner_widget_renders_analysis_only_signals() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    widget = ScannerPreviewWidget()
    widget.set_preview(build_scanner_preview(_series()))

    assert widget.table.rowCount() == 3
    assert "ANALYSE UNIQUEMENT" in widget.safety.text()
    assert "29 bougies" in widget.status.text()
    assert widget.table.item(0, 0).text() == "breakout"
    assert widget.table.item(0, 1).text() in {"BUY", "SELL", "FLAT"}
    assert widget.table.item(0, 2).text() == "INCONNU"
    assert widget.table.item(0, 8).text() == "INDISPONIBLE"
    assert widget.table.item(0, 9).text() == "no_trade"


def test_scanner_quality_tooltip_explains_price_accuracy_limit() -> None:
    from trading_ig_assistant.domain.analysis import ScoreBand, ScoreComponentName
    from trading_ig_assistant.services.scanner_component_service import ScannerComponentService
    from trading_ig_assistant.services.setup_scoring_service import build_banded_score_component

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    preview = build_scanner_preview(_series())
    scores = ScannerComponentService().score_signals(
        preview.consensus,
        build_banded_score_component(ScoreComponentName.CONTEXT, ScoreBand.UNKNOWN),
        fresh=True,
        continuous=True,
    )
    widget = ScannerPreviewWidget()
    widget.set_preview(preview, score_results=scores)
    assert "ne vérifie pas indépendamment" in widget.table.item(0, 7).toolTip()
    widget.close()


def test_main_window_scanner_tab_has_no_order_action() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    window._chart_candle_series = _series(
        trailing_close="129",
        resolution_seconds=60,
    )
    recent_start = datetime.now(UTC).replace(second=0, microsecond=0) - timedelta(minutes=29)
    recent = window._chart_candle_series
    window._chart_candle_series = ChartCandleSeries(
        selected_product_epic=recent.selected_product_epic,
        chart_source_epic=recent.chart_source_epic,
        resolution_seconds=recent.resolution_seconds,
        price_basis=recent.price_basis,
        candles=tuple(
            Candle(
                timestamp=recent_start + timedelta(minutes=index),
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
            )
            for index, candle in enumerate(recent.candles)
        ),
        sources=recent.sources,
    )

    window.scanner_preview.refresh_button.click()
    app.processEvents()

    labels = [window.right_tabs.tabText(index) for index in range(window.right_tabs.count())]
    assert "Scanner" in labels
    assert window.scanner_preview.table.rowCount() == 3
    assert window.scanner_preview.findChildren(QtWidgets.QPushButton) == [
        window.scanner_preview.refresh_button
    ]
    assert "aucun ticket ni ordre" in window.statusBar().currentMessage()
    window.close()
    app.processEvents()


def test_main_window_reports_session_warmup_without_disabling_paper() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    series = _series()
    window._chart_candle_series = ChartCandleSeries(
        selected_product_epic=series.selected_product_epic,
        chart_source_epic=series.chart_source_epic,
        resolution_seconds=series.resolution_seconds,
        price_basis=series.price_basis,
        candles=series.candles[:1],
        sources=series.sources[:1],
    )

    window.scanner_preview.refresh_button.click()
    app.processEvents()

    assert "WARMING_UP" in window.scanner_preview.status.text()
    assert window.product_selector.paper_ticket.isEnabled()
    window.close()
    app.processEvents()


def test_connected_scanner_refresh_uses_exact_bound_session_batch() -> None:
    from trading_ig_assistant.app.config import AppConfig, IGEnvironment
    from trading_ig_assistant.domain.market_data import ChartCandleUpdate
    from trading_ig_assistant.services.market_navigation_catalog_service import (
        IGProductMarketBindingRegistry,
    )
    from trading_ig_assistant.services.multi_market_session_candle_service import (
        MultiMarketSessionCandleService,
    )
    from trading_ig_assistant.ui.main_window import ActiveIGConnection

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    window._config = AppConfig(environment=IGEnvironment.DEMO)
    window._scanner_binding_registry = IGProductMarketBindingRegistry(
        window._config.product_market_bindings
    )
    window._scanner_session_candles = MultiMarketSessionCandleService(
        window._scanner_binding_registry,
        reference_epics=("IX.D.NASDAQ.IFD.IP",),
    )
    buy = TradableProduct(
        epic="IX.D.NASDAQ.OPTCALL2.IP",
        name="US Tech 100 Barrières Achat",
        product_type=ProductType.BARRIER,
        asset_class=AssetClass.INDICES,
        direction=ProductDirection.BUY,
        status="TRADEABLE",
    )
    sell = TradableProduct(
        epic="IX.D.NASDAQ.OPTPUT2.IP",
        name="US Tech 100 Barrières Vente",
        product_type=ProductType.BARRIER,
        asset_class=AssetClass.INDICES,
        direction=ProductDirection.SELL,
        status="TRADEABLE",
    )
    window.product_selector.set_results(
        [
            ProductDiscoveryResult(
                search_term="all",
                candidates_count=2,
                products=[buy, sell],
            )
        ]
    )
    window._selected_product = buy
    window.product_selector.set_selected_product(buy)
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.DEMO,
        current_account_id="DEMO-ACCOUNT",
        accounts=[],
        adapter=type("Adapter", (), {"session": object()})(),
    )
    recent_start = datetime.now(UTC).replace(second=0, microsecond=0) - timedelta(minutes=30)
    for index in range(31):
        value = Decimal("100") + index
        window._scanner_session_candles.ingest_m1_update(
            environment=IGEnvironment.DEMO,
            account_id="DEMO-ACCOUNT",
            chart_update=ChartCandleUpdate(
                epic="IX.D.NASDAQ.IFD.IP",
                interval="1MINUTE",
                timestamp_ms=int((recent_start + timedelta(minutes=index)).timestamp() * 1000),
                end_of_candle=index < 30,
                raw={
                    "BID_OPEN": str(value),
                    "BID_HIGH": str(value + 1),
                    "BID_LOW": str(value - 1),
                    "BID_CLOSE": str(value + Decimal("0.5")),
                    "OFR_OPEN": str(value + Decimal("0.2")),
                    "OFR_HIGH": str(value + Decimal("1.2")),
                    "OFR_LOW": str(value - Decimal("0.8")),
                    "OFR_CLOSE": str(value + Decimal("0.7")),
                },
            ),
            resolution_seconds=60,
            price_basis=ChartPriceBasis.MID,
        )

    window.scanner_preview.refresh_button.click()
    app.processEvents()

    assert window._latest_scanner_runtime_batch is not None
    assert tuple(
        item.product.epic for item in window._latest_scanner_runtime_batch.batch.items
    ) == (buy.epic, sell.epic)
    assert window.scanner_preview.table.rowCount() == 3
    assert "2 produit(s) lié(s)" in window.statusBar().currentMessage()
    assert "aucun ticket ni ordre" in window.statusBar().currentMessage()
    window._active_connection = None
    window.close()
    app.processEvents()


def test_connected_scanner_refuses_unbound_selected_product() -> None:
    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.ui.main_window import ActiveIGConnection

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    product = TradableProduct(
        epic="UNBOUND.PRODUCT",
        name="Unbound",
        product_type=ProductType.CASH_OR_DFB,
        asset_class=AssetClass.INDICES,
    )
    window._selected_product = product
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.DEMO,
        current_account_id="DEMO-ACCOUNT",
        accounts=[],
        adapter=type("Adapter", (), {"session": object()})(),
    )

    window.scanner_preview.refresh_button.click()
    app.processEvents()

    assert "binding exact" in window.scanner_preview.status.text()
    assert window.scanner_preview.table.rowCount() == 0
    assert window.product_selector.paper_ticket.isEnabled()
    window._active_connection = None
    window.close()
    app.processEvents()
