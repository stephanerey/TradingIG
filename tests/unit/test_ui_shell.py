def test_gui_modules_import_without_ig_connectivity() -> None:
    import trading_ig_assistant.ui.about_dialog as about_dialog
    import trading_ig_assistant.ui.account_status_widget as account_status_widget
    import trading_ig_assistant.ui.chart_view as chart_view
    import trading_ig_assistant.ui.macro_ribbon_widget as macro_ribbon_widget
    import trading_ig_assistant.ui.main_window as main_window
    import trading_ig_assistant.ui.product_selector as product_selector
    import trading_ig_assistant.ui.settings_view as settings_view

    assert about_dialog.AboutDialog is not None
    assert account_status_widget.AccountStatusRibbonWidget is not None
    assert chart_view.ChartView is not None
    assert macro_ribbon_widget.MacroRibbonWidget is not None
    assert main_window.MainWindow is not None
    assert product_selector.ProductSelectorWidget is not None
    assert settings_view.SettingsView is not None


def test_chart_model_accepts_sample_ohlc_data() -> None:
    from trading_ig_assistant.ui.chart_view import ChartDataModel, OhlcBar

    bars = [
        OhlcBar(index=0, open=10.0, high=12.0, low=9.5, close=11.5),
        OhlcBar(index=1, open=11.5, high=13.0, low=11.0, close=12.2),
    ]
    model = ChartDataModel()

    model.set_bars(bars)

    assert model.bars == bars
    assert len(ChartDataModel.sample().bars) > 0


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
    assert widget.product_table.item(0, 1).text() == "US Tech 100"
