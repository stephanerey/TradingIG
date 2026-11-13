from datetime import UTC, datetime
from decimal import Decimal

from trading_ig_assistant.app.config import AppConfig, WorkspaceState, load_config
from trading_ig_assistant.app.projections.account import AccountHeaderVM
from trading_ig_assistant.app.projections.account_projection import (
    build_runtime_health_projection,
)
from trading_ig_assistant.app.projections.common import Amount, Availability, DataProvenance
from trading_ig_assistant.app.projections.health import HealthServiceVM
from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
from trading_ig_assistant.app.ui_facade import RuntimeUIFacade


def _application():
    from PyQt5 import QtWidgets

    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_theme_is_centralized_and_resolves_every_qss_token() -> None:
    from trading_ig_assistant.ui.theme.theme_manager import ThemeManager

    stylesheet = ThemeManager().stylesheet()

    assert "#090F1C" in stylesheet
    assert "#2C83F5" in stylesheet
    assert "@BACKGROUND" not in stylesheet
    assert "QLineEdit" in stylesheet
    assert "QComboBox QAbstractItemView" in stylesheet
    assert "QScrollBar::handle:vertical" in stylesheet


def test_theme_applies_dark_control_palette() -> None:
    from PyQt5 import QtGui, QtWidgets

    from trading_ig_assistant.ui.theme.theme_manager import ThemeManager

    app = _application()
    ThemeManager().apply(app)
    line_edit = QtWidgets.QLineEdit("France 40")
    combo = QtWidgets.QComboBox()
    combo.addItem("Compte DEMO")

    assert line_edit.palette().color(QtGui.QPalette.Base).name() == "#101d31"
    assert line_edit.palette().color(QtGui.QPalette.Text).name() == "#eaf1fb"
    assert combo.palette().color(QtGui.QPalette.Base).name() == "#101d31"
    assert combo.palette().color(QtGui.QPalette.Text).name() == "#eaf1fb"


def test_language_manager_switches_fr_en_without_touching_decimal_values() -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager

    app = _application()
    assert app is not None
    amount = Decimal("1234.5600")
    manager = LanguageManager("fr_FR")

    assert manager.text("nav.dashboard") == "Tableau de bord"
    manager.set_locale("en_US")
    assert manager.text("nav.dashboard") == "Dashboard"
    manager.set_locale("fr_FR")
    assert manager.text("nav.dashboard") == "Tableau de bord"
    assert amount == Decimal("1234.5600")


def test_runtime_rejects_snapshots_from_an_old_generation() -> None:
    now = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
    runtime = TradingRuntime(now_provider=lambda: now)
    old_generation = runtime.generation_id
    new_generation = runtime.begin_generation()
    received: list[object] = []
    subscription = runtime.subscribe("account_header", received.append)
    stale = AccountHeaderVM(
        generation_id=old_generation,
        account_id="OLD",
        ig_environment="demo",
        product_account_type="CFD",
        execution_mode="ANALYSIS",
        equity=None,
        available_funds=None,
        day_pnl=None,
        week_pnl=None,
        month_pnl=None,
        open_positions_count=0,
        ig_rest_status="connected",
        ig_stream_status="live",
        ai_status="not_configured",
        generated_at_utc=now,
    )
    current = AccountHeaderVM(
        generation_id=new_generation,
        account_id="CURRENT",
        ig_environment="demo",
        product_account_type="CFD",
        execution_mode="PAPER",
        equity=Amount(
            value=Decimal("1000.00"),
            currency="EUR",
            provenance=DataProvenance(
                source="fixture",
                observed_at_utc=now,
                received_at_utc=now,
                scope="demo/CURRENT",
                availability=Availability.READY,
            ),
        ),
        available_funds=None,
        day_pnl=None,
        week_pnl=None,
        month_pnl=None,
        open_positions_count=0,
        ig_rest_status="connected",
        ig_stream_status="live",
        ai_status="not_configured",
        generated_at_utc=now,
    )

    assert runtime.publish_account_header(stale) is False
    assert runtime.publish_account_header(current) is True
    assert runtime.read_account_header() == current
    assert received == [current]
    subscription.close()


def test_runtime_health_requires_one_generation() -> None:
    now = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
    runtime = TradingRuntime(now_provider=lambda: now)
    health = HealthServiceVM(
        generation_id=0,
        service_id="ig-rest",
        status=Availability.UNAVAILABLE,
        summary="No authenticated session",
        observed_at_utc=now,
        reason_codes=("DISCONNECTED",),
    )

    assert runtime.publish_health((health,), generation_id=0) is True
    assert runtime.read_health() == (health,)


def test_health_does_not_confuse_configuration_or_subscription_with_activity() -> None:
    now = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)

    rest, stream, ai = build_runtime_health_projection(
        generation_id=0,
        rest_status="connected",
        stream_status="subscribed",
        ai_status="configured",
        observed_at_utc=now,
    )

    assert rest.status is Availability.READY
    assert stream.status is Availability.WARMING_UP
    assert ai.status is Availability.WARMING_UP


def test_v2_shell_has_eight_lazy_pages_and_navigation_does_not_change_runtime() -> None:
    from trading_ig_assistant.ui.shell.main_window_v2 import MainWindowV2
    from trading_ig_assistant.ui.shell.page_specs import PAGE_SPECS

    app = _application()
    assert app is not None
    runtime = TradingRuntime()
    generation = runtime.generation_id
    window = MainWindowV2(facade=RuntimeUIFacade(runtime))
    window.resize(1366, 768)
    window.show()
    app.processEvents()

    assert window.router.current_key == "dashboard"
    assert window.stack.count() == 1
    assert window.width() == 1366
    assert window.minimumSizeHint().width() <= 1366
    assert window.minimumSizeHint().height() <= 768
    for spec in PAGE_SPECS:
        window.router.open_page(spec.key)
        assert window.stack.currentWidget().minimumSizeHint().width() <= 1366
        assert window.stack.currentWidget().minimumSizeHint().height() <= 768
    assert window.stack.count() == 8
    assert runtime.generation_id == generation
    assert runtime.read_account_header().ig_rest_status == "disconnected"

    window.set_locale("en_US")
    assert window.windowTitle() == "TradingIG — Analysis and Simulation"
    assert window.sidebar._buttons["scanner"].text() == "Markets / Scanner"
    window.set_locale("fr_FR")
    assert window.sidebar._buttons["scanner"].text() == "Marchés / Scanner"
    window.close()
    app.processEvents()


def test_v2_shell_persists_followed_products_in_separate_account_contexts(
    tmp_path,
) -> None:
    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.ui.shell.main_window_v2 import MainWindowV2

    app = _application()
    config_path = tmp_path / "config.json"
    config = AppConfig()
    window = MainWindowV2(
        config=config,
        config_path=config_path,
        workspace_persistence=True,
    )

    window._activate_watchlist_context(IGEnvironment.DEMO, "DEMO-A")
    window._on_followed_product_epics_changed(("DEMO.FRANCE",))
    window._activate_watchlist_context(IGEnvironment.LIVE, "LIVE-A")
    window._on_followed_product_epics_changed(("LIVE.FRANCE",))
    app.processEvents()

    loaded = load_config(config_path)
    assert loaded.followed_epics_for(IGEnvironment.DEMO, "DEMO-A") == (
        "DEMO.FRANCE",
    )
    assert loaded.followed_epics_for(IGEnvironment.LIVE, "LIVE-A") == (
        "LIVE.FRANCE",
    )

    window.close()
    app.processEvents()


def test_v2_workspace_persists_without_erasing_legacy_splitter(tmp_path) -> None:
    from trading_ig_assistant.ui.shell.main_window_v2 import MainWindowV2

    app = _application()
    assert app is not None
    config_path = tmp_path / "config.json"
    config = AppConfig(
        workspace=WorkspaceState(
            window_width=900,
            window_height=650,
            splitter_sizes=(350, 550),
            active_page="scanner",
        )
    )
    window = MainWindowV2(
        config=config,
        config_path=config_path,
        workspace_persistence=True,
    )
    window.router.open_page("diagnostics")
    window.sidebar.set_collapsed(True)
    window.set_locale("en_US")
    window.resize(1000, 700)
    window.show()
    app.processEvents()
    window.close()
    app.processEvents()

    workspace = load_config(config_path).workspace
    assert workspace.layout_version == 2
    assert workspace.window_width == 1000
    assert workspace.window_height == 700
    assert workspace.active_page == "diagnostics"
    assert workspace.sidebar_collapsed is True
    assert workspace.locale == "en_US"
    assert workspace.splitter_sizes == (350, 550)
    assert workspace.window_geometry


def test_diagnostics_show_observed_health_and_settings_cannot_enable_live() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui.pages.diagnostics_page import DiagnosticsPage
    from trading_ig_assistant.ui.pages.settings_page import SettingsPage
    from trading_ig_assistant.ui.shell.main_window_v2 import MainWindowV2

    app = _application()
    now = datetime(2026, 11, 9, 15, 0, tzinfo=UTC)
    runtime = TradingRuntime(now_provider=lambda: now)
    runtime.publish_stream_status(
        generation_id=runtime.generation_id,
        status="connecting",
        observed_at_utc=now,
    )
    window = MainWindowV2(config=AppConfig(), facade=RuntimeUIFacade(runtime))
    window.router.open_page("diagnostics")
    diagnostics = window.router._pages["diagnostics"]
    assert isinstance(diagnostics, DiagnosticsPage)
    assert diagnostics.health_table.rowCount() == 3

    window.router.open_page("settings")
    settings = window.router._pages["settings"]
    assert isinstance(settings, SettingsPage)
    assert settings.tabs.count() == 8
    assert settings.findChildren(QtWidgets.QCheckBox) == []
    settings.locale_combo.setCurrentIndex(settings.locale_combo.findData("en_US"))
    app.processEvents()
    assert window.language.locale == "en_US"
    assert "cannot be enabled" in settings._summaries[0].text()

    window.close()
    app.processEvents()


def test_v2_corrupt_geometry_falls_back_to_validated_dimensions() -> None:
    from trading_ig_assistant.ui.shell.main_window_v2 import MainWindowV2

    app = _application()
    assert app is not None
    config = AppConfig(
        workspace=WorkspaceState(
            window_width=1100,
            window_height=700,
            window_geometry="not-a-qt-geometry",
        )
    )

    window = MainWindowV2(config=config)

    assert window.width() == 1100
    assert window.height() == 700
    window.close()
    app.processEvents()


def test_legacy_window_publishes_read_only_account_projection_without_new_adapter() -> None:
    from types import SimpleNamespace

    from trading_ig_assistant.app.config import IGEnvironment
    from trading_ig_assistant.domain.instruments import Account
    from trading_ig_assistant.ui.main_window import ActiveIGConnection, MainWindow

    app = _application()
    assert app is not None
    runtime = TradingRuntime()
    adapter = SimpleNamespace(session=None, logout=lambda: None)
    window = MainWindow(projection_runtime=runtime)
    window._active_connection = ActiveIGConnection(
        environment=IGEnvironment.DEMO,
        current_account_id="DEMO-ACCOUNT-1",
        accounts=[
            Account(
                account_id="DEMO-ACCOUNT-1",
                account_name="Demo",
                account_type="CFD",
                currency="EUR",
                balance=1000.0,
            )
        ],
        adapter=adapter,
    )

    window._publish_runtime_projections()

    header = window.ui_facade.read_account_header()
    assert header.account_id == "DEMO-ACCOUNT-1"
    assert header.ig_environment == "demo"
    assert header.product_account_type == "CFD"
    assert header.execution_mode == "PAPER"
    assert header.equity is None
    assert header.ig_rest_status == "connected"
    assert runtime.read_health()[0].service_id == "ig-rest"
    assert runtime.read_health()[0].status is Availability.READY
    assert window.ui_facade.read_dashboard().availability is Availability.READY
    assert window.ui_facade.read_dashboard().equity is None

    previous_generation = runtime.generation_id
    window._clear_connection_market_state()
    assert runtime.generation_id == previous_generation + 1
    assert window.ui_facade.read_account_header().account_id is None
    window._active_connection = None
    window.close()
    app.processEvents()
