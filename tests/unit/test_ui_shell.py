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
                    "snapshotTime": "2026/05/11 10:00:00",
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


def test_chart_view_accepts_live_quote_update() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_data import Quote
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.chart_view import ChartView

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
    assert view._model.bars[0].open > 1000


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
