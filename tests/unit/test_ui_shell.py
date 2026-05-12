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


def test_history_request_spec_targets_longer_windows() -> None:
    from trading_ig_assistant.ui.main_window import _history_request_spec

    assert _history_request_spec(60, "1M") == ("MINUTE", 10_000)
    assert _history_request_spec(300, "1M") == ("MINUTE_5", 8_640)
    assert _history_request_spec(3600, "1Y") == ("HOUR", 8_760)


def test_chart_view_defaults_to_five_minutes_internally() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui.chart_view import ChartView

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    view = ChartView()

    assert view.current_interval_seconds() == 300
    assert view.resolution_combo.currentData() == 300
    assert view.current_range_key() == "1M"


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

    assert chart_product.epic == "IX.D.NASDAQ.IFD.IP"
    assert chart_product.product_type == ProductType.CASH_OR_DFB
    assert "US Tech 100" in adapter.queries


def test_resolve_chart_source_product_override_takes_precedence() -> None:
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
        chart_source_overrides={"us tech 100": "IX.D.NASDAQ.IFD.IP"},
    )

    assert resolved.epic == "IX.D.NASDAQ.IFD.IP"
    assert resolved.product_type == ProductType.CASH_OR_DFB


def test_resolve_chart_source_product_avoids_barrier_candidates_when_cash_exists() -> None:
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

    assert resolved.epic == "IX.D.NASDAQ.IFD.IP"


def test_chart_source_search_terms_include_safe_underlying_candidates() -> None:
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import _chart_source_search_terms

    product = TradableProduct(
        epic="IX.D.NASDAQ.IFD.IP",
        name="US Tech 100",
        product_type=ProductType.CASH_OR_DFB,
    )

    terms = _chart_source_search_terms(product)

    assert "US Tech 100" in terms
    assert "us tech 100" in [term.lower() for term in terms]


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


def test_historical_rest_failure_does_not_prevent_streaming_start(monkeypatch, tmp_path) -> None:
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

        def get_prices(self, epic, **kwargs):
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
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.LIVE,
        current_account_id="ACC123",
        accounts=[],
        adapter=FailingAdapter(),
    )

    window._apply_selected_product_state()

    assert restarted["called"] is True
    assert (
        "No historical cache yet. Live candles will be stored from now on."
        in window.statusBar().currentMessage()
    )


def test_historical_allowance_failure_keeps_streaming_start(monkeypatch, tmp_path) -> None:
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

        def get_prices(self, epic, **kwargs):
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
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.LIVE,
        current_account_id="ACC123",
        accounts=[],
        adapter=FailingAdapter(),
    )

    window._apply_selected_product_state()

    assert restarted["called"] is True
    assert (
        "historical rest allowance" in window.statusBar().currentMessage().lower()
    )


def test_historical_allowance_pause_prevents_automatic_retry(monkeypatch, tmp_path) -> None:
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
    first_call_count = adapter.calls
    window._load_selected_product_history()

    assert first_call_count > 0
    assert adapter.calls == first_call_count
    assert "historical rest allowance reached" in window.statusBar().currentMessage().lower()


def test_cached_history_is_used_when_allowance_is_exhausted(monkeypatch, tmp_path) -> None:
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
        saved_at=datetime(2026, 5, 11, 10, 30, tzinfo=UTC),
    )
    _save_history_cache(
        environment=IGEnvironment.LIVE,
        account_id="ACC123",
        epic=product.epic,
        resolution="MINUTE_5",
        range_key="1M",
        price_basis=ChartPriceBasis.MID.value,
        max_points=8640,
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

    window._load_selected_product_history()

    assert adapter.calls == 0
    assert window.chart_view.display_bar_count() == 1
    assert "using cached history" in window.statusBar().currentMessage().lower()


def test_cached_history_for_chart_source_is_used_when_selected_product_is_barrier(
    monkeypatch, tmp_path
) -> None:
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

    assert window.chart_view.display_bar_count() == 1
    assert window._chart_candle_series is not None
    assert window._chart_candle_series.chart_source_epic == "IX.D.NASDAQ.IFD.IP"
    assert window._chart_candle_series.selected_product_epic == "IX.D.NASDAQ.OPTCALL2.IP"
    assert "using cached history" in window.statusBar().currentMessage().lower()


def test_barrier_history_allowance_failure_falls_back_to_underlying_cash_epic(monkeypatch) -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.instruments import MarketSummary
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import ActiveIGConnection, MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
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

    assert "IX.D.NASDAQ.IFD.IP" in adapter.calls
    assert window._chart_candle_series is not None
    assert window._chart_candle_series.chart_source_epic == "IX.D.NASDAQ.IFD.IP"
    assert window._chart_candle_series.selected_product_epic == "IX.D.NASDAQ.OPTCALL2.IP"


def test_stream_updates_extend_cached_history_series(monkeypatch, tmp_path) -> None:
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
    window.chart_view.resolution_combo.setCurrentIndex(window.chart_view.resolution_combo.findData(300))

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
        saved_at=datetime(2026, 5, 11, 10, 30, tzinfo=UTC),
    )
    _save_history_cache(
        environment=IGEnvironment.LIVE,
        account_id="ACC123",
        epic=product.epic,
        resolution="MINUTE_5",
        range_key="1M",
        price_basis=ChartPriceBasis.MID.value,
        max_points=8640,
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
    assert len(window._chart_candle_series.candles) == initial_count
    assert CandleSource.CACHE in window._chart_candle_series.sources
    assert CandleSource.STREAM in window._chart_candle_series.sources


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
