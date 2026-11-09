import time


def _wait_for_price_history(window, timeout_seconds: float = 3.0) -> None:
    from PyQt5 import QtWidgets

    app = QtWidgets.QApplication.instance()
    assert app is not None
    deadline = time.monotonic() + timeout_seconds
    while window._price_history_thread is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    app.processEvents()
    assert window._price_history_thread is None


def test_gui_modules_import_without_ig_connectivity() -> None:
    import trading_ig_assistant.ui.about_dialog as about_dialog
    import trading_ig_assistant.ui.account_status_widget as account_status_widget
    import trading_ig_assistant.ui.chart_view as chart_view
    import trading_ig_assistant.ui.log_view_dialog as log_view_dialog
    import trading_ig_assistant.ui.macro_ribbon_widget as macro_ribbon_widget
    import trading_ig_assistant.ui.main_window as main_window
    import trading_ig_assistant.ui.paper_portfolio_view as paper_portfolio_view
    import trading_ig_assistant.ui.product_selector as product_selector
    import trading_ig_assistant.ui.settings_view as settings_view
    import trading_ig_assistant.ui.ticket_view as ticket_view

    assert about_dialog.AboutDialog is not None
    assert account_status_widget.AccountStatusRibbonWidget is not None
    assert chart_view.ChartView is not None
    assert log_view_dialog.LogViewDialog is not None
    assert macro_ribbon_widget.MacroRibbonWidget is not None
    assert main_window.MainWindow is not None
    assert paper_portfolio_view.PaperPortfolioWidget is not None
    assert product_selector.ProductSelectorWidget is not None
    assert settings_view.SettingsView is not None
    assert ticket_view.PaperTicketWidget is not None


def test_chart_model_accepts_sample_ohlc_data() -> None:
    from trading_ig_assistant.ui.chart_view import ChartDataModel, OhlcBar

    bars = [
        OhlcBar(timestamp_ms=1_000, open=10.0, high=12.0, low=9.5, close=11.5),
        OhlcBar(timestamp_ms=61_000, open=11.5, high=13.0, low=11.0, close=12.2),
    ]
    model = ChartDataModel()

    model.set_bars(bars)

    assert model.bars == bars
    assert len(ChartDataModel.sample().bars) > 0


def test_chart_model_builds_bars_from_price_series() -> None:
    from trading_ig_assistant.domain.market_data import ChartPriceBasis, PriceSeries
    from trading_ig_assistant.ui.chart_view import ChartDataModel

    model = ChartDataModel.from_price_series(
        PriceSeries(
            epic="EPIC.ONE",
            prices=[
                {
                    "snapshotTimeUTC": "2026-05-11T10:00:00Z",
                    "openPrice": {"bid": 10.0, "offer": 10.4},
                    "highPrice": {"bid": 12.0, "offer": 12.4},
                    "lowPrice": {"bid": 9.5, "offer": 9.9},
                    "closePrice": {"bid": 11.5, "offer": 11.9},
                }
            ],
        ),
        price_basis=ChartPriceBasis.MID,
    )

    assert model.bars[0].timestamp_ms == 1_778_493_600_000
    assert model.bars[0].open == 10.2
    assert model.bars[0].close == 11.7


def test_history_request_spec_targets_a_bounded_recent_snapshot_per_timeframe() -> None:
    from trading_ig_assistant.ui.main_window import _history_request_spec

    assert _history_request_spec(60, "1M") == ("MINUTE", 32)
    assert _history_request_spec(300, "1M") == ("MINUTE_5", 32)
    assert _history_request_spec(3600, "1Y") == ("HOUR", 32)


def test_historical_allowance_metadata_is_extracted() -> None:
    from trading_ig_assistant.ui.main_window import _extract_history_allowance

    assert _extract_history_allowance(
        {
            "metadata": {
                "allowance": {
                    "remainingAllowance": 9123,
                    "totalAllowance": 10000,
                    "allowanceExpiry": 4567,
                }
            }
        }
    ) == (9123, 10000, 4567)
    assert _extract_history_allowance({"prices": []}) is None


def test_historical_allowance_breaker_persists_between_sessions(monkeypatch, tmp_path) -> None:
    from datetime import UTC, datetime, timedelta

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.ui.main_window import (
        HistoricalAllowanceState,
        _load_history_allowance_state,
        _save_history_allowance_state,
    )

    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._history_cache_root",
        lambda: tmp_path,
    )
    observed_at = datetime.now(UTC)
    expected = HistoricalAllowanceState(
        exhausted=True,
        exhausted_at=observed_at,
        last_error="historical allowance",
        blocked_until=observed_at + timedelta(hours=6),
        affected_account_id="ACC123",
        affected_epic="*",
        remaining_points=0,
        total_points=10000,
    )

    _save_history_allowance_state(
        environment=IGEnvironment.LIVE,
        account_id="ACC123",
        state=expected,
    )
    restored = _load_history_allowance_state(
        environment=IGEnvironment.LIVE,
        account_id="ACC123",
    )

    assert restored.is_blocked(account_id="ACC123", epic="ANY")
    assert restored.blocked_until == expected.blocked_until
    assert restored.remaining_points == 0
    assert restored.total_points == 10000


def test_latest_series_gap_key_only_flags_a_gap_at_the_live_edge() -> None:
    from datetime import UTC, datetime, timedelta
    from decimal import Decimal

    from trading_ig_assistant.domain.market_data import (
        Candle,
        CandleSource,
        ChartCandleSeries,
        ChartPriceBasis,
    )
    from trading_ig_assistant.ui.main_window import _latest_series_gap_key

    start = datetime(2026, 11, 5, 10, 0, tzinfo=UTC)

    def series(last_offset: int) -> ChartCandleSeries:
        candles = tuple(
            Candle(
                timestamp=start + timedelta(minutes=offset),
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
            )
            for offset in (0, 1, last_offset)
        )
        return ChartCandleSeries(
            selected_product_epic="SELECTED",
            chart_source_epic="SOURCE",
            resolution_seconds=60,
            price_basis=ChartPriceBasis.MID,
            candles=candles,
            sources=(CandleSource.REST, CandleSource.STREAM),
        )

    assert _latest_series_gap_key(series(2)) is None
    assert _latest_series_gap_key(series(4)) == (
        "SOURCE",
        60,
        (start + timedelta(minutes=1)).isoformat(),
        (start + timedelta(minutes=4)).isoformat(),
    )


def test_streaming_subscribes_to_m1_for_session_aggregation(monkeypatch) -> None:
    from types import SimpleNamespace

    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import ActiveIGConnection, MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    subscriptions = []

    class FakeStreamingAdapter:
        def __init__(self, **_kwargs):
            pass

        def start(self):
            pass

        def stop(self):
            pass

        def subscribe_markets(self, epics):
            subscriptions.append(("markets", tuple(epics)))

        def subscribe_charts(self, epics, scale):
            subscriptions.append(("charts", tuple(epics), scale))

    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window.IGStreamingAdapter",
        FakeStreamingAdapter,
    )
    window = MainWindow()
    window.chart_view.resolution_combo.setCurrentIndex(
        window.chart_view.resolution_combo.findData(3600)
    )
    product = TradableProduct(
        epic="IX.D.NASDAQ.IFD.IP",
        name="US Tech 100",
        product_type=ProductType.CASH_OR_DFB,
    )
    window._selected_product = product
    window._chart_product = product
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.LIVE,
        current_account_id="ACC123",
        accounts=[],
        adapter=SimpleNamespace(
            session=SimpleNamespace(lightstreamer_endpoint="https://stream.example"),
            logout=lambda: None,
        ),
    )
    window._restart_streaming()

    chart_subscription = next(item for item in subscriptions if item[0] == "charts")
    assert chart_subscription == (
        "charts",
        (
            "IX.D.NASDAQ.IFD.IP",
            "IX.D.CAC.IMF.IP",
            "IX.D.DAX.IFMM.IP",
            "CS.D.CFEGOLD.CEF.IP",
            "CC.D.CL.UEF.IP",
        ),
        "1MINUTE",
    )
    assert window._aggregation_mode == "session_m1"
    window._stop_streaming()
    window._active_connection = None


def test_background_reference_chart_accumulates_without_changing_selected_chart() -> None:
    from decimal import Decimal
    from types import SimpleNamespace

    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.market_data import ChartCandleUpdate, ChartPriceBasis
    from trading_ig_assistant.ui.main_window import ActiveIGConnection, MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.DEMO,
        current_account_id="DEMO-ACCOUNT",
        accounts=[],
        adapter=SimpleNamespace(session=None, logout=lambda: None),
    )

    window._on_stream_chart(
        ChartCandleUpdate(
            epic="CS.D.CFEGOLD.CEF.IP",
            interval="1MINUTE",
            timestamp_ms=1_799_164_800_000,
            end_of_candle=True,
            raw={
                "BID_OPEN": "2000.0",
                "BID_HIGH": "2002.0",
                "BID_LOW": "1999.0",
                "BID_CLOSE": "2001.0",
                "OFR_OPEN": "2000.4",
                "OFR_HIGH": "2002.4",
                "OFR_LOW": "1999.4",
                "OFR_CLOSE": "2001.4",
            },
        )
    )

    series = window._scanner_session_candles.reference_series(
        environment=IGEnvironment.DEMO,
        account_id="DEMO-ACCOUNT",
        reference_epic="CS.D.CFEGOLD.CEF.IP",
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
    )
    assert len(series.candles) == 1
    assert series.candles[0].close == Decimal("2001.2")
    assert window._chart_candle_series is None
    window._active_connection = None
    window.close()


def test_multi_chart_permission_error_falls_back_to_selected_chart_only() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import MainWindow

    class FakeStreamingAdapter:
        def __init__(self):
            self.subscriptions = []

        def subscribe_charts(self, epics, scale):
            self.subscriptions.append((tuple(epics), scale))

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    selected = TradableProduct(
        epic="IX.D.NASDAQ.IFD.IP",
        name="US Tech 100",
        product_type=ProductType.CASH_OR_DFB,
    )
    adapter = FakeStreamingAdapter()
    window._selected_product = selected
    window._chart_product = selected
    window._streaming_adapter = adapter
    window._chart_stream_epics = (
        selected.epic,
        "IX.D.CAC.IMF.IP",
        "IX.D.DAX.IFMM.IP",
    )

    window._on_stream_error(
        "Subscription error for CHART:3-markets:1MINUTE: -1 Insufficient permissions"
    )

    assert adapter.subscriptions == [((selected.epic,), "1MINUTE")]
    assert window._chart_stream_epics == (selected.epic,)
    assert window._chart_stream_permission_fallback_attempted is True
    assert "graphique sélectionné continue seul" in window.statusBar().currentMessage()
    window._streaming_adapter = None
    window.close()


def test_price_permission_error_does_not_retry_or_reset_chart_subscriptions() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import MainWindow

    class FakeStreamingAdapter:
        def __init__(self):
            self.subscriptions = []

        def subscribe_charts(self, epics, scale):
            self.subscriptions.append((tuple(epics), scale))

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    selected = TradableProduct(
        epic="REFERENCE", name="Reference", product_type=ProductType.CASH_OR_DFB
    )
    adapter = FakeStreamingAdapter()
    window._selected_product = selected
    window._chart_product = selected
    window._streaming_adapter = adapter
    window._chart_stream_epics = ("REFERENCE", "OTHER")
    original_session = window._scanner_session_candles

    window._on_stream_error("Subscription error for PRICE: -1 Insufficient permissions")

    assert adapter.subscriptions == []
    assert window._chart_stream_epics == ("REFERENCE", "OTHER")
    assert window._scanner_session_candles is original_session
    assert window._chart_stream_permission_fallback_attempted is False
    assert "PRICE" in window.statusBar().currentMessage()
    window._on_stream_error(
        "Subscription error for CHART:3-markets:1MINUTE: -1 Insufficient permissions"
    )
    assert adapter.subscriptions == []
    assert window._scanner_session_candles is original_session
    window._streaming_adapter = None
    window.close()


def test_selected_chart_permission_error_does_not_retry_forever() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import MainWindow

    class FakeStreamingAdapter:
        def __init__(self):
            self.subscriptions = []

        def subscribe_charts(self, epics, scale):
            self.subscriptions.append((tuple(epics), scale))

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    selected = TradableProduct(
        epic="DENIED.SELECTED",
        name="Denied",
        product_type=ProductType.CASH_OR_DFB,
    )
    adapter = FakeStreamingAdapter()
    window._selected_product = selected
    window._chart_product = selected
    window._streaming_adapter = adapter
    window._chart_stream_epics = (selected.epic,)

    window._on_stream_error("Subscription error: -1 Insufficient permissions")

    assert adapter.subscriptions == []
    assert "Insufficient permissions" in window.statusBar().currentMessage()
    window._streaming_adapter = None
    window.close()


def test_selected_chart_permission_error_builds_product_price_candles_only() -> None:
    from datetime import UTC, datetime
    from decimal import Decimal
    from types import SimpleNamespace

    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.market_data import ChartPriceBasis, Quote
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import ActiveIGConnection, MainWindow

    class FakeStreamingAdapter:
        def __init__(self):
            self.probes = []

        def subscribe_charts(self, epics, scale):
            raise AssertionError("selected denied CHART must not be retried")

        def probe_reference_quote(self, epic):
            self.probes.append(epic)

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    selected = TradableProduct(
        epic="IX.D.CAC.OPTCALL2.IP",
        name="France 40 Barrières Achat",
        product_type=ProductType.BARRIER,
    )
    reference = TradableProduct(
        epic="IX.D.CAC.IMF.IP",
        name="France 40",
        product_type=ProductType.CASH_OR_DFB,
    )
    window._selected_product = selected
    window._chart_product = reference
    window._streaming_adapter = FakeStreamingAdapter()
    window._chart_stream_epics = (reference.epic,)
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.LIVE,
        current_account_id="LIVE-ACCOUNT",
        accounts=[],
        adapter=SimpleNamespace(session=None, logout=lambda: None),
    )

    window._on_stream_error(
        "Subscription error for CHART:IX.D.CAC.IMF.IP:1MINUTE: -1 Insufficient permissions"
    )
    window._on_stream_quote(
        Quote(
            epic=selected.epic,
            bid=8057.7,
            offer=8058.5,
            timestamp_ms=int(datetime(2026, 11, 6, 12, 18, tzinfo=UTC).timestamp() * 1000),
        )
    )

    assert window._chart_quote_candle_fallback_active is True
    assert window._streaming_adapter.probes == []
    assert window._chart_product == selected
    assert window._chart_candle_series is not None
    assert window._chart_candle_series.chart_source_epic == selected.epic
    assert window._chart_candle_series.candles[0].close == Decimal("8058.1")
    scanner_series = window._scanner_session_candles.reference_series(
        environment=IGEnvironment.LIVE,
        account_id="LIVE-ACCOUNT",
        reference_epic=reference.epic,
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
    )
    assert scanner_series.candles == ()
    assert "Scanner technique indisponible" in window.statusBar().currentMessage()
    window._streaming_adapter = None
    window._active_connection = None
    window.close()


def test_chart_view_defaults_to_five_minutes_internally() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui.chart_view import ChartView

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    view = ChartView()

    assert view.current_interval_seconds() == 300
    assert view.resolution_combo.currentData() == 300
    assert view.current_range_key() == "1M"


def test_opening_paper_portfolio_refreshes_its_freshness_projection(monkeypatch) -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    calls = []
    monkeypatch.setattr(window, "_refresh_paper_session_views", lambda: calls.append(True))
    window.right_tabs.setCurrentWidget(window.paper_portfolio)
    assert calls == [True]
    window.close()


def test_targeted_search_merges_unique_products_only_for_current_connection() -> None:
    from types import SimpleNamespace

    from PyQt5 import QtWidgets

    from trading_ig_assistant.services.product_discovery_service import ProductDiscoveryResult
    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()
    window.product_selector.set_results([])
    connection = SimpleNamespace(current_account_id="ACCOUNT", adapter=None)
    window._active_connection = connection
    window._targeted_discovery_origin = (connection, "ACCOUNT", window._stream_generation)
    product = _cash_product_for_ui()
    result = ProductDiscoveryResult("targeted-search:Paper", 1, [product])
    window._on_targeted_discovery_success([result])
    window._on_targeted_discovery_success([result])
    assert sum(len(r.products) for r in window.product_selector.results()) == 1
    window.product_selector.set_results([])
    connection.current_account_id = "OTHER"
    window._on_targeted_discovery_success([result])
    assert window.product_selector.results() == []
    window._active_connection = None
    window.close()
    assert app is not None


def test_paper_portfolio_clears_expired_mark_without_a_new_tick() -> None:
    from datetime import UTC, datetime, timedelta

    from PyQt5 import QtCore, QtWidgets

    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()
    clock = [datetime.now(UTC)]
    window._paper_session._now_provider = lambda: clock[0]
    ticket = window.product_selector.paper_ticket
    window.product_selector.set_selected_product(_cash_product_for_ui())
    window.product_selector.set_live_quote(_quote_for_ui())
    clock[0] = datetime.now(UTC) + timedelta(seconds=5)
    ticket.absolute_levels.setChecked(True)
    ticket.quantity.setValue(1.0)
    ticket.stop.setValue(99.0)
    ticket.target.setValue(108.0)
    ticket.request_paper_execution()
    app.processEvents()
    table = window.paper_portfolio.positions_table
    assert table.item(0, 5).text() != "—"
    assert window._paper_freshness_timer.isActive()
    window.paper_portfolio.stop_value.setValue(99.5)
    clock[0] += timedelta(seconds=32)
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(1500, loop.quit)
    loop.exec()
    assert table.item(0, 0).text() == "open"
    assert table.item(0, 5).text() == "—"
    assert table.item(0, 6).text() == "—"
    assert window.paper_portfolio.stop_value.value() == 99.5
    window.right_tabs.setCurrentWidget(window.product_selector)
    assert not window._paper_freshness_timer.isActive()
    window.close()


def test_main_window_can_shrink_to_laptop_viewport() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    window.resize(960, 600)
    window.show()
    app.processEvents()

    assert window.width() == 960
    assert window.height() == 600
    assert window.minimumSizeHint().width() <= 960
    assert window.minimumSizeHint().height() <= 600

    window.close()
    app.processEvents()


def test_main_window_routes_approved_ticket_to_local_paper_views() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    ticket = window.product_selector.paper_ticket
    window.product_selector.set_selected_product(_cash_product_for_ui())
    window.product_selector.set_live_quote(_quote_for_ui())
    ticket.absolute_levels.setChecked(True)
    ticket.quantity.setValue(1.0)
    ticket.stop.setValue(99.0)
    ticket.target.setValue(108.0)

    ticket.request_paper_execution()
    app.processEvents()

    assert window.paper_portfolio.positions_table.rowCount() == 1
    assert window.paper_portfolio.orders_table.rowCount() == 1
    assert window.paper_portfolio.journal_table.rowCount() == 2
    assert window.right_tabs.currentWidget() is window.paper_portfolio
    assert "POSITION PAPER OUVERTE" in ticket.summary.toPlainText()
    window.close()
    app.processEvents()


def test_main_window_controls_selected_position_inside_local_paper_session() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    ticket = window.product_selector.paper_ticket
    window.product_selector.set_selected_product(_cash_product_for_ui())
    window.product_selector.set_live_quote(_quote_for_ui())
    ticket.absolute_levels.setChecked(True)
    ticket.quantity.setValue(1.0)
    ticket.stop.setValue(99.0)
    ticket.target.setValue(108.0)
    ticket.request_paper_execution()
    app.processEvents()

    portfolio = window.paper_portfolio
    assert portfolio.tighten_stop_button.isEnabled()
    assert portfolio.close_position_button.isEnabled()

    portfolio.stop_value.setValue(100.0)
    portfolio.tighten_stop_button.click()
    app.processEvents()

    assert portfolio.positions_table.item(0, 7).text() == "100"
    assert "PAPER_STOP_CONFIRMED" in portfolio.action_result.text()
    assert portfolio.journal_table.rowCount() == 3

    portfolio.close_position_button.click()
    app.processEvents()

    assert portfolio.positions_table.item(0, 0).text() == "closed"
    assert not portfolio.tighten_stop_button.isEnabled()
    assert not portfolio.close_position_button.isEnabled()
    assert "PAPER_POSITION_CLOSED:manual" in portfolio.action_result.text()
    assert portfolio.journal_table.rowCount() == 4
    window.close()
    app.processEvents()


def test_main_window_saves_and_restores_paper_only_on_explicit_actions(tmp_path) -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    database_path = tmp_path / "paper.sqlite"
    source = MainWindow(paper_database_path=database_path)
    assert database_path.exists() is False

    ticket = source.product_selector.paper_ticket
    source.product_selector.set_selected_product(_cash_product_for_ui())
    source.product_selector.set_live_quote(_quote_for_ui())
    ticket.absolute_levels.setChecked(True)
    ticket.quantity.setValue(1.0)
    ticket.stop.setValue(99.0)
    ticket.target.setValue(108.0)
    ticket.request_paper_execution()
    source.paper_portfolio.save_session_button.click()
    app.processEvents()

    assert database_path.exists()
    assert "sauvegardée explicitement" in source.paper_portfolio.persistence_result.text()

    restored = MainWindow(paper_database_path=database_path)
    assert restored.paper_portfolio.positions_table.rowCount() == 0
    restored.paper_portfolio.restore_session_button.click()
    app.processEvents()

    assert restored.paper_portfolio.positions_table.rowCount() == 1
    assert restored.paper_portfolio.orders_table.rowCount() == 1
    assert restored.paper_portfolio.journal_table.rowCount() == 3
    assert restored.paper_portfolio.positions_table.item(0, 0).text() == "open"
    assert "aucune transmission à IG" in restored.paper_portfolio.persistence_result.text()
    source.close()
    restored.close()
    app.processEvents()


def test_empty_paper_save_does_not_create_database(tmp_path) -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    database_path = tmp_path / "paper.sqlite"
    window = MainWindow(paper_database_path=database_path)

    window.paper_portfolio.save_session_button.click()
    app.processEvents()

    assert database_path.exists() is False
    assert "Aucun état Paper" in window.paper_portfolio.persistence_result.text()
    window.close()
    app.processEvents()


def _cash_product_for_ui():
    from trading_ig_assistant.domain.products import ProductType, TradableProduct

    return TradableProduct(
        epic="PAPER.EUR.UI",
        name="Paper UI Market",
        product_type=ProductType.CASH_OR_DFB,
        currency="EUR",
        status="TRADEABLE",
        min_size=1.0,
    )


def test_scanner_flat_fee_model_excludes_share_cfds() -> None:
    from decimal import Decimal

    from trading_ig_assistant.app.config import AppConfig, ScannerExecutionCostConfig
    from trading_ig_assistant.domain.products import AssetClass, ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import _scanner_fee_for_product

    config = AppConfig(
        scanner_execution_costs=ScannerExecutionCostConfig(
            cash_or_dfb_fee_per_unit_per_side=Decimal("0"),
            defaults_initialized=True,
        )
    )
    index = TradableProduct(
        epic="INDEX.CFD",
        name="Index CFD",
        product_type=ProductType.CASH_OR_DFB,
        asset_class=AssetClass.INDICES,
    )
    share = TradableProduct(
        epic="SHARE.CFD",
        name="Share CFD",
        product_type=ProductType.CASH_OR_DFB,
        asset_class=AssetClass.SHARES,
    )

    assert _scanner_fee_for_product(config, index) == Decimal("0")
    assert _scanner_fee_for_product(config, share) is None


def _quote_for_ui():
    from trading_ig_assistant.domain.market_data import Quote

    return Quote(
        epic="PAPER.EUR.UI",
        bid=100.0,
        offer=101.0,
        market_state="TRADEABLE",
    )


def test_main_window_persists_existing_workspace_without_affecting_default_tests(
    monkeypatch,
    tmp_path,
) -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import (
        AppConfig,
        WorkspaceState,
        load_config,
        save_config,
    )
    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    config_path = tmp_path / "config.json"
    save_config(
        AppConfig(
            workspace=WorkspaceState(
                window_width=700,
                window_height=500,
                splitter_sizes=(420, 280),
            )
        ),
        config_path,
    )
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window.default_config_path",
        lambda: config_path,
    )

    window = MainWindow(workspace_persistence=True)

    assert window.width() == 700
    assert window.height() == 500
    window.resize(720, 520)
    window.body_splitter.setSizes([400, 320])
    window.show()
    app.processEvents()
    window.close()
    app.processEvents()

    persisted = load_config(config_path).workspace
    assert persisted.window_width == 720
    assert persisted.window_height == 520
    assert len(persisted.splitter_sizes) == 2
    assert sum(persisted.splitter_sizes) > 0


def test_connection_worker_rejects_unconfirmed_account_switch(monkeypatch) -> None:
    from trading_ig_assistant.adapters.ig_rest import IGSession
    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.instruments import Account
    from trading_ig_assistant.services.ig_connection_service import IGConnectionRequest
    from trading_ig_assistant.ui import main_window as main_window_module

    class UnconfirmedAdapter:
        logged_out = False

        def login(self, _credentials):
            return IGSession(
                cst="fake-cst",
                security_token="fake-token",
                current_account_id="ACCOUNT-A",
            )

        def get_accounts(self):
            return [Account(account_id="ACCOUNT-B", account_name="Synthetic")]

        def switch_account(self, _account_id):
            return IGSession(
                cst="fake-cst",
                security_token="fake-token",
                current_account_id="ACCOUNT-A",
            )

        def logout(self):
            self.logged_out = True

    adapter = UnconfirmedAdapter()
    monkeypatch.setattr(
        main_window_module,
        "IGRestAdapter",
        lambda **_kwargs: adapter,
    )
    worker = main_window_module.ConnectionWorker(
        IGConnectionRequest(
            environment=IGEnvironment.DEMO,
            username="synthetic-user",
            password="fake-password",
            api_key="fake-api-key",
            selected_account_id="ACCOUNT-B",
        )
    )
    failures = []
    successes = []
    worker.failed.connect(failures.append)
    worker.succeeded.connect(successes.append)

    worker.run()

    assert successes == []
    assert failures and "confirm" in failures[0].lower()
    assert adapter.logged_out is True


def test_connection_worker_skips_switch_when_selected_account_is_already_active(
    monkeypatch,
) -> None:
    from trading_ig_assistant.adapters.ig_rest import IGSession
    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.instruments import Account
    from trading_ig_assistant.services.ig_connection_service import IGConnectionRequest
    from trading_ig_assistant.ui import main_window as main_window_module

    class AlreadyActiveAdapter:
        def login(self, _credentials):
            return IGSession(
                cst="fake-cst",
                security_token="fake-token",
                current_account_id="ACCOUNT-A",
            )

        def get_accounts(self):
            return [Account(account_id="ACCOUNT-A", account_name="Synthetic")]

        def switch_account(self, _account_id):
            raise AssertionError("the already active IG account must not be switched")

        def logout(self):
            raise AssertionError("a successful GUI connection remains open")

    monkeypatch.setattr(
        main_window_module,
        "IGRestAdapter",
        lambda **_kwargs: AlreadyActiveAdapter(),
    )
    worker = main_window_module.ConnectionWorker(
        IGConnectionRequest(
            environment=IGEnvironment.DEMO,
            username="synthetic-user",
            password="fake-password",
            api_key="fake-api-key",
            selected_account_id="ACCOUNT-A",
        )
    )
    failures = []
    successes = []
    worker.failed.connect(failures.append)
    worker.succeeded.connect(successes.append)

    worker.run()

    assert failures == []
    assert len(successes) == 1
    assert successes[0].current_account_id == "ACCOUNT-A"


def test_chart_scale_for_interval_uses_true_five_minute_stream() -> None:
    from trading_ig_assistant.services.candle_aggregation_service import chart_scale_for_interval

    assert chart_scale_for_interval(60) == "1MINUTE"
    assert chart_scale_for_interval(300) == "5MINUTE"
    assert chart_scale_for_interval(900) == "15MINUTE"


def test_chart_view_history_range_selector_emits_changes() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui.chart_view import ChartView

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    view = ChartView()
    seen = []
    view.history_range_changed.connect(seen.append)

    view.range_combo.setCurrentIndex(view.range_combo.findData("3M"))

    assert view.current_range_key() == "3M"
    assert seen[-1] == "3M"


def test_chart_option_changes_are_unavailable_for_snapshot_and_live() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_data import Quote
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.chart_view import ChartView

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    view = ChartView()
    option = TradableProduct(
        epic="OPTION",
        name="Option",
        product_type=ProductType.OPTION,
        net_change=9900.5,
        percent_change=1.89,
    )
    view.set_selected_product(option)
    assert view.change_label.text() == "Variation: -"
    assert "pas vérifiée" in view.change_label.toolTip()
    view.set_live_quote(
        Quote(epic="OPTION", bid=139, offer=149, net_change=9900.5, percent_change=1.89)
    )
    assert view.bid_label.text() == "Vente: 139.0"
    assert view.change_label.text() == "Variation: -"
    assert view.percent_change_label.text() == "% Variation: -"
    underlying = TradableProduct(
        epic="CFD", name="CFD", product_type=ProductType.CASH_OR_DFB, net_change=12
    )
    view.set_selected_product(underlying)
    assert view.change_label.text() == "Variation: +12"
    assert view.change_label.toolTip() == ""
    view.close()


def test_chart_view_accepts_live_quote_update() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_data import ChartCandleUpdate, Quote
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.chart_view import ChartView, OhlcBar

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    view = ChartView()
    view.resolution_combo.setCurrentIndex(view.resolution_combo.findData(60))
    view.set_selected_product(
        TradableProduct(
            epic="EPIC.ONE",
            name="US Tech 100",
            product_type=ProductType.BARRIER,
            bid=29171.2,
            offer=29172.9,
        )
    )
    view.set_live_quote(
        Quote(
            epic="EPIC.ONE",
            bid=2311.9,
            offer=2313.1,
            net_change=-38.7,
            percent_change=-1.64,
            market_state="TRADEABLE",
        )
    )

    assert "2311.9" in view.bid_label.text()
    assert "2313.1" in view.offer_label.text()
    assert view._model.bars == []
    view.set_bars(
        [
            OhlcBar(
                timestamp_ms=1_778_496_600_000,
                open=29190.0,
                high=29200.0,
                low=29180.0,
                close=29195.0,
            ),
            OhlcBar(
                timestamp_ms=1_778_496_660_000,
                open=29195.0,
                high=29205.0,
                low=29190.0,
                close=29200.0,
            ),
        ]
    )

    view._on_zoom_requested(0.85)
    assert view._manual_zoom is True

    view.apply_chart_update(
        ChartCandleUpdate(
            epic="EPIC.ONE",
            interval="1MINUTE",
            timestamp_ms=1_778_496_600_000,
            open=29190.0,
            high=29210.0,
            low=29180.0,
            close=29200.0,
            end_of_candle=True,
        )
    )

    assert len(view._model.bars) == 2
    assert view._model.bars[0].close == 29200.0
    assert view._model.bars[0].high == 29210.0
    assert view._manual_zoom is True
    assert view._live_price_label is not None


def test_chart_view_live_line_uses_selected_price_basis() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_data import ChartPriceBasis, Quote
    from trading_ig_assistant.ui.chart_view import ChartView, OhlcBar

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    view = ChartView()
    view.set_bars(
        [
            OhlcBar(
                timestamp_ms=1_778_496_600_000,
                open=100.0,
                high=102.0,
                low=99.0,
                close=101.0,
            )
        ]
    )
    quote = Quote(epic="EPIC.ONE", bid=100.0, offer=101.0)

    view.price_basis_combo.setCurrentIndex(view.price_basis_combo.findData(ChartPriceBasis.BID))
    view.set_live_quote(quote)
    assert view._live_price_line is not None
    assert view._live_price_line.value() == 100.0

    view.price_basis_combo.setCurrentIndex(view.price_basis_combo.findData(ChartPriceBasis.ASK))
    view.set_live_quote(quote)
    assert view._live_price_line.value() == 101.0

    view.price_basis_combo.setCurrentIndex(view.price_basis_combo.findData(ChartPriceBasis.MID))
    view.set_live_quote(quote)
    assert view._live_price_line.value() == 100.5


def test_price_basis_change_reloads_selected_product_history_once(monkeypatch, tmp_path) -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.market_data import ChartPriceBasis
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import ActiveIGConnection, MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window.default_config_path",
        lambda: tmp_path / "config.json",
    )
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._discovery_cache_path",
        lambda _environment: tmp_path / "discovery.json",
    )
    window = MainWindow()
    calls = []

    class Adapter:
        session = object()

    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.LIVE,
        current_account_id="ACC123",
        accounts=[],
        adapter=Adapter(),
    )
    window._selected_product = TradableProduct(
        epic="IX.D.NASDAQ.IFD.IP",
        name="US Tech 100",
        product_type=ProductType.CASH_OR_DFB,
    )
    monkeypatch.setattr(window, "_load_selected_product_history", lambda: calls.append("reload"))

    window.chart_view.price_basis_combo.setCurrentIndex(
        window.chart_view.price_basis_combo.findData(ChartPriceBasis.BID)
    )

    assert calls == ["reload"]


def test_price_basis_change_without_connection_does_not_reload(monkeypatch, tmp_path) -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_data import ChartPriceBasis
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window.default_config_path",
        lambda: tmp_path / "config.json",
    )
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._discovery_cache_path",
        lambda _environment: tmp_path / "discovery.json",
    )
    window = MainWindow()
    calls = []
    window._selected_product = TradableProduct(
        epic="IX.D.NASDAQ.IFD.IP",
        name="US Tech 100",
        product_type=ProductType.CASH_OR_DFB,
    )
    monkeypatch.setattr(window, "_load_selected_product_history", lambda: calls.append("reload"))

    window.chart_view.price_basis_combo.setCurrentIndex(
        window.chart_view.price_basis_combo.findData(ChartPriceBasis.BID)
    )

    assert calls == []


def test_price_basis_change_without_selected_product_does_not_reload(monkeypatch, tmp_path) -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.market_data import ChartPriceBasis
    from trading_ig_assistant.ui.main_window import ActiveIGConnection, MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window.default_config_path",
        lambda: tmp_path / "config.json",
    )
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._discovery_cache_path",
        lambda _environment: tmp_path / "discovery.json",
    )
    window = MainWindow()
    calls = []

    class Adapter:
        session = object()

    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.LIVE,
        current_account_id="ACC123",
        accounts=[],
        adapter=Adapter(),
    )
    monkeypatch.setattr(window, "_load_selected_product_history", lambda: calls.append("reload"))

    window.chart_view.price_basis_combo.setCurrentIndex(
        window.chart_view.price_basis_combo.findData(ChartPriceBasis.BID)
    )

    assert calls == []


def test_compressed_axis_maps_candles_without_time_gaps() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui.chart_view import ChartView, OhlcBar

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    view = ChartView()
    first = OhlcBar(timestamp_ms=1_778_496_600_000, open=100.0, high=102.0, low=99.0, close=101.0)
    second = OhlcBar(
        timestamp_ms=1_779_101_400_000,
        open=101.0,
        high=103.0,
        low=100.0,
        close=102.0,
    )

    view.set_bars([first, second])

    assert view._display_bars[0].display_x == 0.0
    assert view._display_bars[1].display_x == 1.0
    assert view._timestamp_ms_for_x(1.0) == second.timestamp_ms


def test_quote_from_chart_update_uses_day_change_fields() -> None:
    from trading_ig_assistant.domain.market_data import ChartCandleUpdate
    from trading_ig_assistant.ui.main_window import _quote_from_chart_update

    quote = _quote_from_chart_update(
        ChartCandleUpdate(
            epic="EPIC.ONE",
            interval="1MINUTE",
            timestamp_ms=1_778_496_600_000,
            close=29195.0,
            raw={
                "BID_CLOSE": "29194.8",
                "OFR_CLOSE": "29195.3",
                "DAY_NET_CHG_MID": "-37.3",
                "DAY_PERC_CHG_MID": "-0.13",
            },
        )
    )

    assert quote is not None
    assert quote.epic == "EPIC.ONE"
    assert quote.bid == 29194.8
    assert quote.offer == 29195.3
    assert quote.net_change == -37.3
    assert quote.percent_change == -0.13


def test_account_status_widget_accepts_account_data(qtbot=None) -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.instruments import Account
    from trading_ig_assistant.ui.account_status_widget import AccountStatusRibbonWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    widget = AccountStatusRibbonWidget()
    widget.set_accounts(
        [
            Account(
                account_id="ACC123456",
                account_name="Live CFD",
                account_type="CFD",
                currency="EUR",
                balance=1000.0,
                available=900.0,
                deposit=1000.0,
                profit_loss=-100.0,
            )
        ],
        "ACC123456",
        IGEnvironment.LIVE,
        connected=False,
    )

    assert widget is not None


def test_account_status_widget_displays_auth_lockout() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui.account_status_widget import AccountStatusRibbonWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    widget = AccountStatusRibbonWidget()
    widget.set_auth_locked("IG authentication locked: too many failed attempts.")

    assert "too many failed attempts" in widget.layout().itemAt(3).widget().text().lower()


def test_settings_profile_widget_shows_secret_presence() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.adapters.credentials import IGCredentials
    from trading_ig_assistant.app.config import IGConnectionProfileConfig, IGEnvironment
    from trading_ig_assistant.ui.settings_dialog import ConnectionProfileWidget

    class FakeStore:
        def load_profile(self, profile_key: str, username: str):
            if profile_key == "demo" and username == "sreytradingdemo":
                return IGCredentials("sreytradingdemo", "demo-pass", "demo-key")
            return None

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    widget = ConnectionProfileWidget(
        IGEnvironment.DEMO,
        IGConnectionProfileConfig(environment=IGEnvironment.DEMO, identifier="sreytradingdemo"),
        FakeStore(),
    )

    text = widget.diagnostic.text().lower()
    assert "id=ok" in text
    assert "stored" in text
    assert "api key" in text


def test_resolve_account_id_prefers_last_selected_account() -> None:
    from trading_ig_assistant.domain.instruments import Account
    from trading_ig_assistant.ui.main_window import _resolve_account_id

    accounts = [
        Account(account_id="CFD", account_name="CFD", preferred=True),
        Account(account_id="BARRIER", account_name="Barrier"),
    ]

    assert _resolve_account_id(accounts, "BARRIER", "CFD") == "BARRIER"
    assert _resolve_account_id(accounts, "MISSING", "CFD") == "CFD"
    assert _resolve_account_id(accounts, "MISSING", "OTHER") == "CFD"


def test_resolve_chart_source_product_does_not_infer_from_cached_name_match() -> None:
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.services.product_discovery_service import ProductDiscoveryResult
    from trading_ig_assistant.ui.main_window import _resolve_chart_source_product

    selected = TradableProduct(
        epic="IX.D.NASDAQ.OPTCALL2.IP",
        name="US Tech 100 BarriÃ¨res Achat",
        product_type=ProductType.BARRIER,
    )
    underlying = TradableProduct(
        epic="IX.D.NASDAQ.IFD.IP",
        name="US Tech 100",
        product_type=ProductType.CASH_OR_DFB,
    )
    results = [
        ProductDiscoveryResult(
            search_term="US Tech 100",
            candidates_count=2,
            products=[selected, underlying],
        )
    ]

    chart_product = _resolve_chart_source_product(selected, results)

    assert chart_product is selected


def test_resolve_chart_source_product_does_not_search_without_explicit_mapping() -> None:
    from trading_ig_assistant.domain.instruments import MarketSummary
    from trading_ig_assistant.domain.products import ProductDirection, ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import _resolve_chart_source_product

    class FakeAdapter:
        def __init__(self):
            self.queries = []

        def search_markets(self, query: str):
            self.queries.append(query)
            return [
                MarketSummary(
                    epic="IX.D.NASDAQ.IFD.IP",
                    instrument_name="US Tech 100",
                    instrument_type="INDICES",
                    market_status="TRADEABLE",
                )
            ]

    selected = TradableProduct(
        epic="IX.D.NASDAQ.OPTCALL2.IP",
        name="US Tech 100 Barrières Achat",
        product_type=ProductType.BARRIER,
        direction=ProductDirection.BUY,
    )

    adapter = FakeAdapter()
    chart_product = _resolve_chart_source_product(selected, [], adapter)

    assert chart_product is selected
    assert adapter.queries == []


def test_resolve_chart_source_product_exact_epic_override_takes_precedence() -> None:
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import _resolve_chart_source_product

    selected = TradableProduct(
        epic="IX.D.NASDAQ.OPTCALL2.IP",
        name="US Tech 100 BarriÃƒÂ¨res Achat",
        product_type=ProductType.BARRIER,
    )
    resolved = _resolve_chart_source_product(
        selected,
        [],
        chart_source_overrides={"IX.D.NASDAQ.OPTCALL2.IP": "IX.D.NASDAQ.IFD.IP"},
    )

    assert resolved.epic == "IX.D.NASDAQ.IFD.IP"
    assert resolved.product_type == ProductType.CASH_OR_DFB


def test_resolve_chart_source_product_ignores_unmapped_barrier_and_cash_candidates() -> None:
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.services.product_discovery_service import ProductDiscoveryResult
    from trading_ig_assistant.ui.main_window import _resolve_chart_source_product

    selected = TradableProduct(
        epic="IX.D.NASDAQ.OPTCALL2.IP",
        name="US Tech 100 BarriÃƒÂ¨res Achat",
        product_type=ProductType.BARRIER,
    )
    barrier_candidate = TradableProduct(
        epic="IX.D.NASDAQ.OPTPUT2.IP",
        name="US Tech 100 Barrier Put",
        product_type=ProductType.BARRIER,
        instrument_type="INDICES",
        status="TRADEABLE",
    )
    cash_candidate = TradableProduct(
        epic="IX.D.NASDAQ.IFD.IP",
        name="US Tech 100",
        product_type=ProductType.CASH_OR_DFB,
        instrument_type="INDICES",
        status="TRADEABLE",
    )
    resolved = _resolve_chart_source_product(
        selected,
        [
            ProductDiscoveryResult(
                search_term="US Tech 100",
                candidates_count=3,
                products=[selected, barrier_candidate, cash_candidate],
            )
        ],
    )

    assert resolved is selected


def test_resolve_chart_source_product_logs_selected_and_chart_source(caplog) -> None:
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.services.product_discovery_service import ProductDiscoveryResult
    from trading_ig_assistant.ui.main_window import _resolve_chart_source_product

    selected = TradableProduct(
        epic="IX.D.NASDAQ.OPTCALL2.IP",
        name="US Tech 100 BarriÃ¨res Achat",
        product_type=ProductType.BARRIER,
    )
    underlying = TradableProduct(
        epic="IX.D.NASDAQ.IFD.IP",
        name="US Tech 100",
        product_type=ProductType.CASH_OR_DFB,
    )
    results = [
        ProductDiscoveryResult(
            search_term="US Tech 100",
            candidates_count=2,
            products=[selected, underlying],
        )
    ]

    caplog.set_level("DEBUG")
    resolved = _resolve_chart_source_product(
        selected,
        results,
        chart_source_overrides={selected.epic: underlying.epic},
    )

    assert resolved.epic == "IX.D.NASDAQ.IFD.IP"
    assert "selected_product_epic=IX.D.NASDAQ.OPTCALL2.IP" in caplog.text
    assert "chart_source_epic=IX.D.NASDAQ.IFD.IP" in caplog.text


def test_session_mode_starts_streaming_without_historical_rest(monkeypatch, tmp_path) -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import ActiveIGConnection, MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._history_cache_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._stream_candle_cache_root",
        lambda: tmp_path,
    )
    window = MainWindow()

    class FailingAdapter:
        session = object()

        def __init__(self):
            self.calls = 0

        def get_prices(self, epic, **kwargs):
            self.calls += 1
            raise RuntimeError("history failed")

    product = TradableProduct(
        epic="IX.D.NASDAQ.IFD.IP",
        name="US Tech 100",
        product_type=ProductType.CASH_OR_DFB,
    )
    restarted = {"called": False}

    monkeypatch.setattr(window, "_restart_streaming", lambda: restarted.__setitem__("called", True))
    window._selected_product = product
    window._chart_product = product
    adapter = FailingAdapter()
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.LIVE,
        current_account_id="ACC123",
        accounts=[],
        adapter=adapter,
    )

    window._apply_selected_product_state()
    _wait_for_price_history(window)

    assert restarted["called"] is True
    assert adapter.calls == 0
    assert "aucun historique REST/cache" in window.statusBar().currentMessage()


def test_session_mode_ignores_historical_allowance_and_keeps_streaming(
    monkeypatch, tmp_path
) -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.adapters.ig_rest import IGAPIError
    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import ActiveIGConnection, MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._history_cache_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._stream_candle_cache_root",
        lambda: tmp_path,
    )
    window = MainWindow()

    class FailingAdapter:
        session = object()

        def __init__(self):
            self.calls = 0

        def get_prices(self, epic, **kwargs):
            self.calls += 1
            raise IGAPIError(
                "HTTP 403: {'errorCode': "
                "'error.public-api.exceeded-account-historical-data-allowance'}"
            )

    product = TradableProduct(
        epic="EPIC.ONE",
        name="US Tech 100 BarriÃƒÂ¨res Achat",
        product_type=ProductType.BARRIER,
    )
    restarted = {"called": False}

    monkeypatch.setattr(window, "_restart_streaming", lambda: restarted.__setitem__("called", True))
    window._selected_product = product
    window._chart_product = product
    adapter = FailingAdapter()
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.LIVE,
        current_account_id="ACC123",
        accounts=[],
        adapter=adapter,
    )

    window._apply_selected_product_state()
    _wait_for_price_history(window)

    assert restarted["called"] is True
    assert adapter.calls == 0
    assert "aucun historique rest/cache" in window.statusBar().currentMessage().lower()


def test_session_mode_never_probes_historical_allowance(monkeypatch, tmp_path) -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import ActiveIGConnection, MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._history_cache_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._stream_candle_cache_root",
        lambda: tmp_path,
    )
    window = MainWindow()

    class FailingAdapter:
        session = object()

        def __init__(self):
            self.calls = 0

        def get_prices(self, epic, **kwargs):
            self.calls += 1
            raise RuntimeError(
                "HTTP 403 {'errorCode': "
                "'error.public-api.exceeded-account-historical-data-allowance'}"
            )

    adapter = FailingAdapter()
    product = TradableProduct(
        epic="IX.D.NASDAQ.OPTCALL2.IP",
        name="US Tech 100 BarriÃƒÂ¨res Achat",
        product_type=ProductType.BARRIER,
    )
    window._selected_product = product
    window._chart_product = product
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.LIVE,
        current_account_id="ACC123",
        accounts=[],
        adapter=adapter,
    )

    window._load_selected_product_history()
    _wait_for_price_history(window)
    window._load_selected_product_history()

    assert adapter.calls == 0
    assert "aucun historique rest/cache" in window.statusBar().currentMessage().lower()


def test_session_mode_does_not_start_a_slow_historical_worker(monkeypatch, tmp_path) -> None:
    import threading

    from PyQt5 import QtCore, QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.market_data import PriceSeries
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import ActiveIGConnection, MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._history_cache_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._stream_candle_cache_root",
        lambda: tmp_path,
    )
    started = threading.Event()

    class SlowAdapter:
        session = object()

        def get_prices(self, epic, **kwargs):
            started.set()
            return PriceSeries(epic=epic, prices=[])

    product = TradableProduct(
        epic="IX.D.NASDAQ.IFD.IP",
        name="US Tech 100",
        product_type=ProductType.CASH_OR_DFB,
    )
    window = MainWindow()
    window._selected_product = product
    window._chart_product = product
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.LIVE,
        current_account_id="ACC123",
        accounts=[],
        adapter=SlowAdapter(),
    )

    before = time.monotonic()
    window._load_selected_product_history()
    elapsed = time.monotonic() - before

    assert elapsed < 0.2
    assert not started.wait(0.05)
    assert window._price_history_thread is None
    timer_fired: list[bool] = []
    QtCore.QTimer.singleShot(0, lambda: timer_fired.append(True))
    app.processEvents()
    assert timer_fired == [True]


def test_persisted_history_is_not_used_in_session_mode(monkeypatch, tmp_path) -> None:
    from datetime import UTC, datetime

    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.market_data import ChartPriceBasis, PriceSeries
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import (
        ActiveIGConnection,
        CachedHistoryEntry,
        HistoricalAllowanceState,
        MainWindow,
        _save_history_cache,
    )

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._history_cache_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._stream_candle_cache_root",
        lambda: tmp_path,
    )
    window = MainWindow()

    class SilentAdapter:
        session = object()

        def __init__(self):
            self.calls = 0

        def get_prices(self, epic, **kwargs):
            self.calls += 1
            raise AssertionError("REST history should not be called while allowance is exhausted")

    adapter = SilentAdapter()
    product = TradableProduct(
        epic="IX.D.NASDAQ.IFD.IP",
        name="US Tech 100",
        product_type=ProductType.CASH_OR_DFB,
    )
    entry = CachedHistoryEntry(
        series=PriceSeries(
            epic=product.epic,
            prices=[
                {
                    "snapshotTimeUTC": "2026-05-11T10:00:00Z",
                    "openPrice": {"bid": 100.0, "offer": 100.2},
                    "highPrice": {"bid": 101.0, "offer": 101.2},
                    "lowPrice": {"bid": 99.5, "offer": 99.7},
                    "closePrice": {"bid": 100.5, "offer": 100.7},
                }
            ],
        ),
        saved_at=datetime.now(UTC),
    )
    _save_history_cache(
        environment=IGEnvironment.LIVE,
        account_id="ACC123",
        epic=product.epic,
        resolution="MINUTE_5",
        range_key="1M",
        price_basis=ChartPriceBasis.MID.value,
        max_points=32,
        entry=entry,
    )
    window._selected_product = product
    window._chart_product = product
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.LIVE,
        current_account_id="ACC123",
        accounts=[],
        adapter=adapter,
    )
    window._history_allowance_state = HistoricalAllowanceState(
        exhausted=True,
        exhausted_at=datetime.now(UTC),
        last_error="historical allowance",
        affected_account_id="ACC123",
        affected_epic="*",
    )
    window._api_allowance_exceeded = True

    window._load_selected_product_history()

    assert adapter.calls == 0
    assert window.chart_view.display_bar_count() == 0
    assert window._chart_candle_series is not None
    assert window._chart_candle_series.sources == ()
    assert "aucun historique rest/cache" in window.statusBar().currentMessage().lower()


def test_persisted_chart_source_history_is_not_used_in_session_mode(monkeypatch, tmp_path) -> None:
    from datetime import UTC, datetime

    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.market_data import ChartPriceBasis, PriceSeries
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import (
        ActiveIGConnection,
        CachedHistoryEntry,
        HistoricalAllowanceState,
        MainWindow,
        _save_history_cache,
    )

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._history_cache_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._stream_candle_cache_root",
        lambda: tmp_path,
    )
    window = MainWindow()

    class SilentAdapter:
        session = object()

        def get_prices(self, epic, **kwargs):
            raise AssertionError("REST history should not be called while allowance is exhausted")

    selected = TradableProduct(
        epic="IX.D.NASDAQ.OPTCALL2.IP",
        name="US Tech 100 BarriÃ¨res Achat",
        product_type=ProductType.BARRIER,
    )
    chart_source = TradableProduct(
        epic="IX.D.NASDAQ.IFD.IP",
        name="US Tech 100",
        product_type=ProductType.CASH_OR_DFB,
        instrument_type="INDICES",
        status="TRADEABLE",
    )
    entry = CachedHistoryEntry(
        series=PriceSeries(
            epic=chart_source.epic,
            prices=[
                {
                    "snapshotTimeUTC": "2026-05-11T10:00:00Z",
                    "openPrice": {"bid": 100.0, "offer": 100.2},
                    "highPrice": {"bid": 101.0, "offer": 101.2},
                    "lowPrice": {"bid": 99.5, "offer": 99.7},
                    "closePrice": {"bid": 100.5, "offer": 100.7},
                }
            ],
        ),
        saved_at=datetime.now(UTC),
    )
    _save_history_cache(
        environment=IGEnvironment.LIVE,
        account_id="ACC123",
        epic=chart_source.epic,
        resolution="MINUTE_5",
        range_key="1M",
        price_basis=ChartPriceBasis.MID.value,
        max_points=32,
        entry=entry,
    )
    window._selected_product = selected
    window._chart_product = chart_source
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.LIVE,
        current_account_id="ACC123",
        accounts=[],
        adapter=SilentAdapter(),
    )
    window._history_allowance_state = HistoricalAllowanceState(
        exhausted=True,
        exhausted_at=datetime.now(UTC),
        last_error="historical allowance",
        affected_account_id="ACC123",
        affected_epic="*",
    )

    window._load_selected_product_history()

    assert window.chart_view.display_bar_count() == 0
    assert window._chart_candle_series is not None
    assert window._chart_candle_series.chart_source_epic == "IX.D.NASDAQ.IFD.IP"
    assert window._chart_candle_series.selected_product_epic == "IX.D.NASDAQ.OPTCALL2.IP"
    assert window._chart_candle_series.sources == ()


def test_stale_history_and_sparse_stream_caches_are_not_restored(monkeypatch, tmp_path) -> None:
    from datetime import UTC, datetime

    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.market_data import (
        ChartCandleUpdate,
        ChartPriceBasis,
        PriceSeries,
    )
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.services.candle_history_service import CandleHistoryService
    from trading_ig_assistant.ui.main_window import (
        ActiveIGConnection,
        CachedHistoryEntry,
        HistoricalAllowanceState,
        MainWindow,
        _save_history_cache,
    )

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._history_cache_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._stream_candle_cache_root",
        lambda: tmp_path,
    )
    window = MainWindow()
    window.chart_view.resolution_combo.setCurrentIndex(
        window.chart_view.resolution_combo.findData(300)
    )

    class SilentAdapter:
        session = object()

        def get_prices(self, epic, **kwargs):
            raise AssertionError("REST history should not be called while allowance is exhausted")

    selected = TradableProduct(
        epic="IX.D.NASDAQ.OPTCALL2.IP",
        name="US Tech 100 Barrières Achat",
        product_type=ProductType.BARRIER,
    )
    chart_source = TradableProduct(
        epic="IX.D.NASDAQ.IFD.IP",
        name="US Tech 100",
        product_type=ProductType.CASH_OR_DFB,
    )
    entry = CachedHistoryEntry(
        series=PriceSeries(
            epic=chart_source.epic,
            prices=[
                {
                    "snapshotTimeUTC": "2026-05-11T10:00:00Z",
                    "openPrice": {"bid": 100.0, "offer": 100.2},
                    "highPrice": {"bid": 101.0, "offer": 101.2},
                    "lowPrice": {"bid": 99.5, "offer": 99.7},
                    "closePrice": {"bid": 100.5, "offer": 100.7},
                },
                {
                    "snapshotTimeUTC": "2026-05-11T10:05:00Z",
                    "openPrice": {"bid": 100.5, "offer": 100.7},
                    "highPrice": {"bid": 101.5, "offer": 101.7},
                    "lowPrice": {"bid": 100.0, "offer": 100.2},
                    "closePrice": {"bid": 101.0, "offer": 101.2},
                },
            ],
        ),
        saved_at=datetime(2026, 5, 11, 10, 30, tzinfo=UTC),
    )
    _save_history_cache(
        environment=IGEnvironment.LIVE,
        account_id="ACC123",
        epic=chart_source.epic,
        resolution="MINUTE_5",
        range_key="1M",
        price_basis=ChartPriceBasis.MID.value,
        max_points=8640,
        entry=entry,
    )
    CandleHistoryService(cache_root_provider=lambda: tmp_path).apply_stream_update(
        environment=IGEnvironment.LIVE,
        account_id="ACC123",
        selected_product_epic=selected.epic,
        chart_source_epic=chart_source.epic,
        resolution_seconds=300,
        price_basis=ChartPriceBasis.MID,
        chart_update=ChartCandleUpdate(
            epic=chart_source.epic,
            interval="5MINUTE",
            timestamp_ms=int(datetime(2026, 5, 11, 10, 10, tzinfo=UTC).timestamp() * 1000),
            end_of_candle=True,
            raw={
                "BID_OPEN": "101.0",
                "BID_HIGH": "102.0",
                "BID_LOW": "100.8",
                "BID_CLOSE": "101.5",
                "OFR_OPEN": "101.2",
                "OFR_HIGH": "102.2",
                "OFR_LOW": "101.0",
                "OFR_CLOSE": "101.7",
            },
        ),
    )
    window._selected_product = selected
    window._chart_product = chart_source
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.LIVE,
        current_account_id="ACC123",
        accounts=[],
        adapter=SilentAdapter(),
    )
    window._history_allowance_state = HistoricalAllowanceState(
        exhausted=True,
        exhausted_at=datetime.now(UTC),
        last_error="historical allowance",
        affected_account_id="ACC123",
        affected_epic="*",
    )

    window._load_selected_product_history()

    assert window._chart_candle_series is not None
    assert window._chart_candle_series.candles == ()
    assert window.chart_view.display_bar_count() == 0
    assert "aucun historique rest/cache" in window.statusBar().currentMessage().lower()


def test_session_mode_does_not_attempt_a_rest_history_fallback(monkeypatch, tmp_path) -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.instruments import MarketSummary
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import ActiveIGConnection, MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._history_cache_root",
        lambda: tmp_path,
    )
    window = MainWindow()

    class Adapter:
        session = object()

        def __init__(self):
            self.calls = []

        def search_markets(self, query):
            return [
                MarketSummary(
                    epic="IX.D.NASDAQ.IFD.IP",
                    instrument_name="US Tech 100",
                    instrument_type="INDICES",
                    market_status="TRADEABLE",
                )
            ]

        def get_prices(self, epic, **kwargs):
            self.calls.append(epic)
            if epic == "IX.D.NASDAQ.OPTCALL2.IP":
                raise RuntimeError(
                    "HTTP 403 {'errorCode': "
                    "'error.public-api.exceeded-account-historical-data-allowance'}"
                )
            return type(
                "Series",
                (),
                {
                    "epic": epic,
                    "prices": [
                        {
                            "snapshotTimeUTC": "2026-05-11T10:00:00Z",
                            "openPrice": {"bid": 100.0, "offer": 100.2},
                            "highPrice": {"bid": 101.0, "offer": 101.2},
                            "lowPrice": {"bid": 99.5, "offer": 99.7},
                            "closePrice": {"bid": 100.5, "offer": 100.7},
                        }
                    ],
                },
            )()

    adapter = Adapter()
    selected = TradableProduct(
        epic="IX.D.NASDAQ.OPTCALL2.IP",
        name="US Tech 100 BarriÃ¨res Achat",
        product_type=ProductType.BARRIER,
    )
    window._selected_product = selected
    window._chart_product = selected
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.LIVE,
        current_account_id="ACC123",
        accounts=[],
        adapter=adapter,
    )

    window._load_selected_product_history()
    _wait_for_price_history(window)

    assert adapter.calls == []
    assert window._chart_candle_series is not None
    assert window._chart_candle_series.chart_source_epic == selected.epic
    assert window._chart_candle_series.selected_product_epic == "IX.D.NASDAQ.OPTCALL2.IP"


def test_stream_updates_build_only_the_current_session_series(monkeypatch, tmp_path) -> None:
    from datetime import UTC, datetime

    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.market_data import (
        CandleSource,
        ChartCandleUpdate,
        ChartPriceBasis,
        PriceSeries,
    )
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import (
        ActiveIGConnection,
        CachedHistoryEntry,
        HistoricalAllowanceState,
        MainWindow,
        _save_history_cache,
    )

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._history_cache_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "trading_ig_assistant.ui.main_window._stream_candle_cache_root",
        lambda: tmp_path,
    )
    window = MainWindow()
    window.chart_view.resolution_combo.setCurrentIndex(
        window.chart_view.resolution_combo.findData(300)
    )

    class SilentAdapter:
        session = object()

        def get_prices(self, epic, **kwargs):
            raise AssertionError("REST history should not be called while allowance is exhausted")

    product = TradableProduct(
        epic="IX.D.NASDAQ.IFD.IP",
        name="US Tech 100",
        product_type=ProductType.CASH_OR_DFB,
    )
    entry = CachedHistoryEntry(
        series=PriceSeries(
            epic=product.epic,
            prices=[
                {
                    "snapshotTimeUTC": "2026-05-11T10:00:00Z",
                    "openPrice": {"bid": 100.0, "offer": 100.2},
                    "highPrice": {"bid": 101.0, "offer": 101.2},
                    "lowPrice": {"bid": 99.5, "offer": 99.7},
                    "closePrice": {"bid": 100.5, "offer": 100.7},
                }
            ],
        ),
        saved_at=datetime.now(UTC),
    )
    _save_history_cache(
        environment=IGEnvironment.LIVE,
        account_id="ACC123",
        epic=product.epic,
        resolution="MINUTE_5",
        range_key="1M",
        price_basis=ChartPriceBasis.MID.value,
        max_points=32,
        entry=entry,
    )
    window._selected_product = product
    window._chart_product = product
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.LIVE,
        current_account_id="ACC123",
        accounts=[],
        adapter=SilentAdapter(),
    )
    window._history_allowance_state = HistoricalAllowanceState(
        exhausted=True,
        exhausted_at=datetime.now(UTC),
        last_error="historical allowance",
        affected_account_id="ACC123",
        affected_epic="*",
    )

    window._load_selected_product_history()
    initial_count = len(window._chart_candle_series.candles if window._chart_candle_series else ())

    window._on_stream_chart(
        ChartCandleUpdate(
            epic=product.epic,
            interval="1MINUTE",
            timestamp_ms=1_778_493_720_000,
            open=100.8,
            high=101.5,
            low=100.7,
            close=101.3,
            end_of_candle=True,
            raw={
                "BID_OPEN": "100.8",
                "BID_HIGH": "101.4",
                "BID_LOW": "100.7",
                "BID_CLOSE": "101.2",
                "OFR_OPEN": "101.0",
                "OFR_HIGH": "101.6",
                "OFR_LOW": "100.9",
                "OFR_CLOSE": "101.4",
            },
        )
    )

    assert window._chart_candle_series is not None
    assert initial_count == 0
    assert len(window._chart_candle_series.candles) == 1
    assert window._chart_candle_series.sources == (CandleSource.STREAM,)


def test_product_selector_displays_discovery_results() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.services.product_discovery_service import ProductDiscoveryResult
    from trading_ig_assistant.ui.product_selector import ProductSelectorWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    widget = ProductSelectorWidget()
    widget.set_results(
        [
            ProductDiscoveryResult(
                search_term="US Tech 100",
                candidates_count=1,
                products=[
                    TradableProduct(
                        epic="EPIC.ONE",
                        name="US Tech 100",
                        product_type=ProductType.CASH_OR_DFB,
                    )
                ],
            )
        ]
    )

    assert widget.product_table.rowCount() == 1
    assert widget.product_table.item(0, 0).text() == "US Tech 100"

    widget.filter_box.setText("missing")
    assert widget.product_table.rowCount() == 0


def test_barrier_name_exposure_is_display_only_and_does_not_change_ticket_direction() -> None:
    from PyQt5 import QtCore, QtWidgets

    from trading_ig_assistant.domain.products import ProductDirection, ProductType, TradableProduct
    from trading_ig_assistant.services.product_discovery_service import ProductDiscoveryResult
    from trading_ig_assistant.ui.product_selector import ProductSelectorWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    widget = ProductSelectorWidget()
    buy = TradableProduct(
        epic="UP", name="France 40 Barrières Achat", product_type=ProductType.BARRIER
    )
    sell = TradableProduct(
        epic="DOWN", name="France 40 Barrières Vente", product_type=ProductType.BARRIER
    )
    unknown = TradableProduct(epic="OTHER", name="Autre Barrière", product_type=ProductType.BARRIER)
    widget.set_results([ProductDiscoveryResult("test", 3, [buy, sell, unknown])])
    table = widget.product_table
    assert table.item(0, 5).text() == "haussière (nom)"
    assert table.item(1, 5).text() == "baissière (nom)"
    assert table.item(2, 5).text() == "unknown"
    assert "sens d'un ordre" in table.item(1, 5).toolTip()
    assert table.item(1, 0).data(QtCore.Qt.UserRole).direction is ProductDirection.UNKNOWN
    original_side = widget.paper_ticket.direction.currentData()
    widget.set_selected_product(sell)
    assert widget.paper_ticket.direction.currentData() == original_side
    assert app is not None


def test_product_selector_displays_conservative_context_per_product() -> None:
    from datetime import UTC, datetime

    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.macro_context import DirectionalBias, EventRisk
    from trading_ig_assistant.domain.products import (
        AssetClass,
        ProductType,
        TradableProduct,
    )
    from trading_ig_assistant.services.macro_context_service import MacroContextService
    from trading_ig_assistant.services.product_discovery_service import ProductDiscoveryResult
    from trading_ig_assistant.ui.product_selector import (
        PRODUCT_CONTEXT_COLUMN,
        ProductSelectorWidget,
    )

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    now = datetime(2026, 11, 5, 13, 0, tzinfo=UTC)
    empty = MacroContextService().build_state((), now)
    state = empty.__class__(
        schema_version=empty.schema_version,
        regime=empty.regime,
        index_bias=DirectionalBias.BULLISH,
        gold_bias=empty.gold_bias,
        event_risk=EventRisk.LOW,
        signals=(),
        generated_at_utc=now,
        reason_codes=(),
        provenance=("source:fixture",),
    )
    widget = ProductSelectorWidget()
    widget.set_market_context(state)
    widget.set_results(
        [
            ProductDiscoveryResult(
                search_term="US Tech 100",
                candidates_count=1,
                products=[
                    TradableProduct(
                        epic="EPIC.ONE",
                        name="US Tech 100 Barrières Achat",
                        product_type=ProductType.BARRIER,
                        asset_class=AssetClass.INDICES,
                    )
                ],
            )
        ]
    )

    context_item = widget.product_table.item(0, PRODUCT_CONTEXT_COLUMN)
    assert context_item.text().startswith("ALIGNÉ 75/100 | index:bullish | event:low")
    assert "ni recommandation, ni probabilité" in context_item.toolTip()


def test_product_context_palette_follows_validated_five_level_order() -> None:
    from trading_ig_assistant.services.product_context_projection_service import (
        ProductContextLevel,
    )
    from trading_ig_assistant.ui.product_selector import PRODUCT_CONTEXT_COLORS
    from trading_ig_assistant.ui.scanner_view import CONTEXT_COLORS

    expected = {
        ProductContextLevel.CATALYST: ("#ffffff", "#075c36"),
        ProductContextLevel.ALIGNED: ("#0f6b3e", "#dff3e7"),
        ProductContextLevel.CAUTION: ("#7a4d00", "#fff3cd"),
        ProductContextLevel.UNFAVORABLE: ("#a61b1b", "#fde7e7"),
        ProductContextLevel.UNKNOWN: ("#4f5965", "#eef1f4"),
    }

    assert PRODUCT_CONTEXT_COLORS == expected
    assert CONTEXT_COLORS == expected


def test_product_selector_updates_live_quote_and_details() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_data import Quote
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.services.product_discovery_service import ProductDiscoveryResult
    from trading_ig_assistant.ui.product_selector import ProductSelectorWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    widget = ProductSelectorWidget()
    product = TradableProduct(
        epic="EPIC.ONE",
        name="US Tech 100",
        product_type=ProductType.CASH_OR_DFB,
        bid=100.0,
        offer=101.0,
    )
    widget.set_results(
        [
            ProductDiscoveryResult(
                search_term="US Tech 100",
                candidates_count=1,
                products=[product],
            )
        ]
    )
    widget.set_selected_product(product)
    widget.set_live_quote(
        Quote(
            epic="EPIC.ONE",
            bid=123.4,
            offer=124.5,
            net_change=2.3,
            percent_change=1.9,
            market_state="TRADEABLE",
        )
    )

    assert widget.product_table.item(0, 1).text() == "123.4"
    assert widget.product_table.item(0, 2).text() == "124.5"
    assert "Snapshot vente: 100" in widget.market_summary.toPlainText()
    assert "Live vente: 123.4" in widget.market_summary.toPlainText()


def test_option_unverified_changes_hidden_for_snapshot_and_live_quote() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_data import Quote
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.services.product_discovery_service import ProductDiscoveryResult
    from trading_ig_assistant.ui.product_selector import ProductSelectorWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    widget = ProductSelectorWidget()
    product = TradableProduct(
        epic="OPTION",
        name="Option",
        product_type=ProductType.OPTION,
        net_change=9900.5,
        percent_change=1.89,
    )
    widget.set_results(
        [ProductDiscoveryResult(search_term="Option", candidates_count=1, products=[product])]
    )
    widget.set_selected_product(product)
    assert widget.product_table.item(0, 3).text() == "-"
    assert "pas vérifiée" in widget.product_table.item(0, 3).toolTip()
    widget.set_live_quote(
        Quote(epic="OPTION", bid=139, offer=149, net_change=9900.5, percent_change=1.89)
    )
    assert widget.product_table.item(0, 1).text() == "139"
    assert widget.product_table.item(0, 3).text() == "-"
    assert widget.product_table.item(0, 4).text() == "-"
    assert "signification IG non vérifiée" in widget.market_summary.toPlainText()
    widget.close()


def test_filtering_preserves_session_quote_without_refreshing_ticket_freshness() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_data import Quote
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.services.product_discovery_service import ProductDiscoveryResult
    from trading_ig_assistant.ui.product_selector import ProductSelectorWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    widget = ProductSelectorWidget()
    product = TradableProduct(
        epic="EPIC", name="Market", product_type=ProductType.CASH_OR_DFB, bid=10, offer=11
    )
    widget.set_results(
        [ProductDiscoveryResult(search_term="x", candidates_count=1, products=[product])]
    )
    widget.set_selected_product(product)
    assert "Snapshot" in widget.product_table.item(0, 1).toolTip()
    widget.set_live_quote(Quote(epic="EPIC", bid=100, offer=101))
    received_at = widget.paper_ticket._quote_received_at_utc
    widget.filter_box.setText("Market")
    assert widget.product_table.item(0, 1).text() == "100"
    assert "session" in widget.product_table.item(0, 1).toolTip()
    assert widget.paper_ticket._quote_received_at_utc == received_at
    widget.clear_live_quotes()
    assert widget.product_table.item(0, 1).text() == "-"
    assert "invalidée" in widget.product_table.item(0, 1).toolTip()
    widget.close()


def test_scanner_session_quote_expires_and_rejects_delayed_or_future_time() -> None:
    from datetime import UTC, datetime, timedelta

    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_data import Quote
    from trading_ig_assistant.ui.product_selector import ProductSelectorWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    widget = ProductSelectorWidget()
    quote = Quote(epic="EPIC", bid=100, offer=101)
    widget.set_live_quote(quote)
    received = datetime(2026, 11, 6, 14, 0, tzinfo=UTC)
    widget._live_quote_received_at["EPIC"] = received
    assert widget.fresh_live_quote_for_epic("EPIC", now=received + timedelta(seconds=30)) == quote
    assert widget.fresh_live_quote_for_epic("EPIC", now=received + timedelta(seconds=31)) is None
    assert widget.fresh_live_quote_for_epic("EPIC", now=received - timedelta(seconds=1)) is None
    widget.set_live_quote(Quote(epic="EPIC", bid=100, offer=101, raw={"DELAY": "1"}))
    assert widget.fresh_live_quote_for_epic("EPIC", now=datetime.now(UTC)) is None
    widget.clear_live_quotes()
    assert widget.fresh_live_quote_for_epic("EPIC", now=received) is None
    widget.close()


def test_account_switch_clears_live_quotes_and_ticket_authorization() -> None:
    from types import SimpleNamespace

    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.market_data import Quote
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.services.product_discovery_service import ProductDiscoveryResult
    from trading_ig_assistant.ui.main_window import ActiveIGConnection, MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    product = TradableProduct(epic="EPIC", name="Market", product_type=ProductType.CASH_OR_DFB)
    window.product_selector.set_results(
        [ProductDiscoveryResult(search_term="x", candidates_count=1, products=[product])]
    )
    window.product_selector.set_selected_product(product)
    window.product_selector.set_live_quote(Quote(epic="EPIC", bid=100, offer=101))
    window.product_selector.paper_ticket.last_outcome_approved = True
    window.product_selector.paper_ticket.execute_button.setEnabled(True)
    window.scanner_preview.table.setRowCount(1)
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.DEMO,
        current_account_id="OLD",
        accounts=[],
        adapter=SimpleNamespace(
            switch_account=lambda _account: SimpleNamespace(current_account_id="NEW")
        ),
    )

    assert window._switch_active_account("NEW") is True
    assert window.product_selector.live_quote_for_epic("EPIC") is None
    assert window.product_selector.product_table.item(0, 1).text() == "-"
    assert window.product_selector.paper_ticket._quote is None
    assert not window.product_selector.paper_ticket.last_outcome_approved
    assert not window.product_selector.paper_ticket.execute_button.isEnabled()
    assert window.scanner_preview.table.rowCount() == 0
    assert "compte courant" in window.scanner_preview.status.text()
    assert (
        "Cotation précédente invalidée"
        in window.product_selector.paper_ticket.summary.toPlainText()
    )
    window._active_connection = None
    window.close()


def test_stale_stream_events_are_ignored_after_stream_stop() -> None:
    from PyQt5 import QtCore, QtWidgets

    from trading_ig_assistant.app.streaming_bridge import StreamingEventBridge
    from trading_ig_assistant.domain.market_data import Quote
    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    old_bridge = StreamingEventBridge(window._stream_generation)
    old_bridge.quote_received.connect(window._on_current_stream_quote, QtCore.Qt.QueuedConnection)
    old_bridge.error_received.connect(window._on_current_stream_error, QtCore.Qt.QueuedConnection)
    old_bridge.on_quote(Quote(epic="OLD", bid=100, offer=101))
    old_bridge.on_stream_error("OLD ERROR")
    window._stop_streaming()
    app.processEvents()
    assert window.product_selector.live_quote_for_epic("OLD") is None
    assert "OLD ERROR" not in window.statusBar().currentMessage()

    current = StreamingEventBridge(window._stream_generation)
    current.quote_received.connect(window._on_current_stream_quote)
    current.on_quote(Quote(epic="NEW", bid=200, offer=201))
    app.processEvents()
    assert window.product_selector.live_quote_for_epic("NEW") is not None
    window.close()


def test_failed_account_switch_invalidates_quote_when_account_state_is_uncertain() -> None:
    from types import SimpleNamespace

    from PyQt5 import QtWidgets

    from trading_ig_assistant.adapters.ig_rest import IGAPIError
    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.market_data import Quote
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import ActiveIGConnection, MainWindow

    def failed_switch(_account):
        raise IGAPIError("switch not confirmed")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    product = TradableProduct(epic="EPIC", name="Market", product_type=ProductType.CASH_OR_DFB)
    window.product_selector.set_selected_product(product)
    window.product_selector.set_live_quote(Quote(epic="EPIC", bid=100, offer=101))
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.DEMO,
        current_account_id="OLD",
        accounts=[],
        adapter=SimpleNamespace(switch_account=failed_switch),
    )

    assert window._switch_active_account("NEW") is False
    assert window.product_selector.live_quote_for_epic("EPIC") is None
    assert window.product_selector.paper_ticket._quote is None
    assert "Account switch failed" in window.statusBar().currentMessage()
    window._active_connection = None
    window.close()


def test_failed_account_selection_does_not_save_or_display_unconfirmed_account(monkeypatch) -> None:
    from types import SimpleNamespace

    from PyQt5 import QtWidgets

    from trading_ig_assistant.adapters.ig_rest import IGAPIError
    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.ui.main_window import ActiveIGConnection, MainWindow

    def failed_switch(_account):
        raise IGAPIError("switch not confirmed")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    saved = []
    logged_out = []
    monkeypatch.setattr(window, "_set_profile_account", lambda *args: saved.append(args))
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.DEMO,
        current_account_id="OLD",
        accounts=[],
        adapter=SimpleNamespace(
            switch_account=failed_switch, logout=lambda: logged_out.append(True)
        ),
    )

    window._select_account("NEW")

    assert window._active_connection is None
    assert not window.account_status._connected
    assert saved == []
    assert logged_out == [True]
    assert "Account switch failed" in window.statusBar().currentMessage()
    window.close()


def test_switch_response_for_different_account_is_rejected() -> None:
    from types import SimpleNamespace

    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.ui.main_window import ActiveIGConnection, MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.DEMO,
        current_account_id="OLD",
        accounts=[],
        adapter=SimpleNamespace(
            switch_account=lambda _account: SimpleNamespace(current_account_id="OTHER")
        ),
    )
    assert window._switch_active_account("REQUESTED") is False
    assert window._active_connection.current_account_id == "OLD"
    assert "Account switch failed" in window.statusBar().currentMessage()
    window._active_connection = None
    window.close()


def test_product_selector_exposes_visible_epics_from_active_tab() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.services.product_discovery_service import ProductDiscoveryResult
    from trading_ig_assistant.ui.product_selector import ProductSelectorWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    widget = ProductSelectorWidget()
    widget.set_results(
        [
            ProductDiscoveryResult(
                search_term="cached",
                candidates_count=2,
                products=[
                    TradableProduct(
                        epic="EPIC.ONE",
                        name="US Tech 100",
                        product_type=ProductType.CASH_OR_DFB,
                    ),
                    TradableProduct(
                        epic="EPIC.TWO",
                        name="US 500",
                        product_type=ProductType.CASH_OR_DFB,
                    ),
                ],
            )
        ]
    )

    assert widget.visible_price_epics()[:2] == ["EPIC.ONE", "EPIC.TWO"]


def test_selected_product_is_first_in_capped_price_subscription() -> None:
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import (
        PRODUCT_STREAM_ITEMS_LIMIT,
        _prioritized_price_epics,
    )

    selected = TradableProduct(
        epic="SELECTED.BARRIER",
        name="Selected Barrier",
        product_type=ProductType.BARRIER,
    )
    chart_source = TradableProduct(
        epic="CHART.UNDERLYING",
        name="Chart Underlying",
        product_type=ProductType.CASH_OR_DFB,
    )
    visible = [f"VISIBLE.{index}" for index in range(PRODUCT_STREAM_ITEMS_LIMIT + 5)]

    subscribed = _prioritized_price_epics(selected, visible, chart_source)[
        :PRODUCT_STREAM_ITEMS_LIMIT
    ]

    assert subscribed[0] == selected.epic
    assert selected.epic in subscribed
    assert len(subscribed) == PRODUCT_STREAM_ITEMS_LIMIT


def test_selected_chart_source_is_added_before_the_bounded_baseline_universe() -> None:
    from trading_ig_assistant.domain.market_navigation import initial_ig_reference_epics
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import _prioritized_chart_epics

    selected_source = TradableProduct(
        epic="CUSTOM.REFERENCE",
        name="Custom reference",
        product_type=ProductType.CASH_OR_DFB,
    )

    subscribed = _prioritized_chart_epics(selected_source, initial_ig_reference_epics())

    assert subscribed[0] == "CUSTOM.REFERENCE"
    assert subscribed[1:] == list(initial_ig_reference_epics())
    assert len(subscribed) == 6
