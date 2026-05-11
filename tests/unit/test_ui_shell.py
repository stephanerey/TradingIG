def test_gui_modules_import_without_ig_connectivity() -> None:
    import trading_ig_assistant.ui.about_dialog as about_dialog
    import trading_ig_assistant.ui.account_status_widget as account_status_widget
    import trading_ig_assistant.ui.chart_view as chart_view
    import trading_ig_assistant.ui.log_view_dialog as log_view_dialog
    import trading_ig_assistant.ui.macro_ribbon_widget as macro_ribbon_widget
    import trading_ig_assistant.ui.main_window as main_window
    import trading_ig_assistant.ui.product_selector as product_selector
    import trading_ig_assistant.ui.settings_view as settings_view

    assert about_dialog.AboutDialog is not None
    assert account_status_widget.AccountStatusRibbonWidget is not None
    assert chart_view.ChartView is not None
    assert log_view_dialog.LogViewDialog is not None
    assert macro_ribbon_widget.MacroRibbonWidget is not None
    assert main_window.MainWindow is not None
    assert product_selector.ProductSelectorWidget is not None
    assert settings_view.SettingsView is not None


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
    from trading_ig_assistant.domain.market_data import PriceSeries
    from trading_ig_assistant.ui.chart_view import ChartDataModel

    model = ChartDataModel.from_price_series(
        PriceSeries(
            epic="EPIC.ONE",
            prices=[
                {
                    "snapshotTimeUTC": "2026-05-11T10:00:00Z",
                    "openPrice": {"bid": 10.0},
                    "highPrice": {"bid": 12.0},
                    "lowPrice": {"bid": 9.5},
                    "closePrice": {"bid": 11.5},
                }
            ],
        )
    )

    assert model.bars[0].timestamp_ms == 1_778_493_600_000
    assert model.bars[0].open == 10.0
    assert model.bars[0].close == 11.5


def test_history_request_spec_targets_longer_windows() -> None:
    from trading_ig_assistant.ui.main_window import _history_request_spec

    assert _history_request_spec(60) == ("MINUTE", 500)
    assert _history_request_spec(300) == ("MINUTE_5", 600)
    assert _history_request_spec(3600) == ("HOUR", 500)


def test_chart_view_accepts_live_quote_update() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_data import ChartCandleUpdate, Quote
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.chart_view import ChartView, OhlcBar

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    view = ChartView()
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


def test_resolve_chart_source_product_prefers_underlying_cash_market() -> None:
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

    assert chart_product.epic == "IX.D.NASDAQ.IFD.IP"
    assert chart_product.product_type == ProductType.CASH_OR_DFB


def test_resolve_chart_source_product_uses_targeted_search_when_results_miss_cash_market() -> None:
    from trading_ig_assistant.domain.instruments import MarketSummary
    from trading_ig_assistant.domain.products import ProductDirection, ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import _resolve_chart_source_product

    class FakeAdapter:
        def search_markets(self, query: str):
            assert query == "us tech 100"
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

    chart_product = _resolve_chart_source_product(selected, [], FakeAdapter())

    assert chart_product.epic == "IX.D.NASDAQ.IFD.IP"
    assert chart_product.product_type == ProductType.CASH_OR_DFB


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
    resolved = _resolve_chart_source_product(selected, results)

    assert resolved.epic == "IX.D.NASDAQ.IFD.IP"
    assert "selected_product_epic=IX.D.NASDAQ.OPTCALL2.IP" in caplog.text
    assert "chart_source_epic=IX.D.NASDAQ.IFD.IP" in caplog.text


def test_historical_rest_failure_does_not_prevent_streaming_start(monkeypatch) -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import ActiveIGConnection, MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()

    class FailingAdapter:
        session = object()

        def get_prices(self, epic, **kwargs):
            raise RuntimeError("history failed")

    product = TradableProduct(
        epic="EPIC.ONE",
        name="US Tech 100 BarriÃ¨res Achat",
        product_type=ProductType.BARRIER,
    )
    restarted = {"called": False}

    monkeypatch.setattr(window, "_restart_streaming", lambda: restarted.__setitem__("called", True))
    window._selected_product = product
    window._chart_product = product
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.LIVE,
        current_account_id="ACC123",
        accounts=[],
        adapter=FailingAdapter(),
    )

    window._apply_selected_product_state()

    assert restarted["called"] is True
    assert (
        "Historical backfill unavailable; live chart is running."
        in window.statusBar().currentMessage()
    )


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
