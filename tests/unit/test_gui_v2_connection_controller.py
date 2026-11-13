from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from threading import Event

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.adapters.credentials import IGCredentials
from trading_ig_assistant.adapters.ig_rest import IGSession
from trading_ig_assistant.app.config import (
    AppConfig,
    IGConnectionProfileConfig,
    IGEnvironment,
)
from trading_ig_assistant.app.qt_connection_controller import ReadOnlyConnectionController
from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
from trading_ig_assistant.app.ui_facade import RuntimeUIFacade
from trading_ig_assistant.domain.instruments import Account


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class FakeCredentialStore:
    def __init__(self) -> None:
        self.profile_keys: list[str] = []

    def load_profile(self, profile_key: str, username: str) -> IGCredentials | None:
        self.profile_keys.append(profile_key)
        return IGCredentials(
            username=username,
            password="fake-password",
            api_key="fake-api-key",
        )


class FakeReadOnlyAdapter:
    def __init__(self) -> None:
        self.logged_out = False
        self.switch_calls: list[str] = []

    def login(self, _credentials: IGCredentials) -> IGSession:
        return IGSession(
            cst="fake-cst",
            security_token="fake-token",
            current_account_id="DEMO-A",
        )

    def get_accounts(self) -> list[Account]:
        return [
            Account(
                account_id="DEMO-A",
                account_name="Demo CFD",
                account_type="CFD",
                currency="EUR",
                balance=10000.0,
                available=9250.5,
                deposit=500.0,
                profit_loss=-249.5,
            ),
            Account(
                account_id="DEMO-B",
                account_name="Demo Options",
                account_type="OPTIONS",
                currency="EUR",
                balance=15000.0,
                available=14000.0,
                deposit=750.0,
                profit_loss=125.0,
            ),
        ]

    def switch_account(self, account_id: str) -> IGSession:
        self.switch_calls.append(account_id)
        return IGSession(
            cst="fake-cst",
            security_token="fake-token",
            current_account_id=account_id,
        )

    def logout(self) -> None:
        self.logged_out = True


def _config() -> AppConfig:
    config = AppConfig()
    config.connection_profiles[IGEnvironment.DEMO] = IGConnectionProfileConfig(
        environment=IGEnvironment.DEMO,
        identifier="synthetic-user",
    )
    config.connection_profiles[IGEnvironment.LIVE] = IGConnectionProfileConfig(
        environment=IGEnvironment.LIVE,
        identifier="synthetic-live-user",
    )
    return config


def _wait_until_idle(controller: ReadOnlyConnectionController) -> None:
    if not controller.busy:
        return
    loop = QtCore.QEventLoop()
    timed_out: list[bool] = []

    def on_busy_changed(busy: bool) -> None:
        if not busy:
            loop.quit()

    def on_timeout() -> None:
        timed_out.append(True)
        loop.quit()

    controller.busy_changed.connect(on_busy_changed)
    QtCore.QTimer.singleShot(3000, on_timeout)
    loop.exec()
    controller.busy_changed.disconnect(on_busy_changed)
    assert not timed_out
    assert controller.busy is False


def test_v2_controller_connects_and_switches_only_through_read_only_runtime(tmp_path) -> None:
    app = _application()
    adapter = FakeReadOnlyAdapter()
    factory_calls: list[IGEnvironment] = []
    runtime = TradingRuntime(
        now_provider=lambda: datetime(2026, 11, 9, 12, 0, tzinfo=UTC),
        ig_adapter_factory=lambda environment: factory_calls.append(environment) or adapter,
    )
    saved_accounts: list[str | None] = []
    config = _config()
    controller = ReadOnlyConnectionController(
        runtime=runtime,
        config=config,
        config_path=tmp_path / "config.json",
        credential_store=FakeCredentialStore(),
        save_config_fn=lambda current, _path: saved_accounts.append(
            current.connection_profiles[IGEnvironment.DEMO].selected_account_id
        ),
        now_provider=lambda: datetime(2026, 11, 9, 12, 0, tzinfo=UTC),
    )

    assert factory_calls == []
    controller.connect_demo()
    _wait_until_idle(controller)
    app.processEvents()

    assert factory_calls == [IGEnvironment.DEMO]
    assert runtime.active_ig_connection is not None
    assert runtime.read_account_header().account_id == "DEMO-A"
    assert runtime.read_account_header().equity is None
    assert runtime.read_account_header().account_balance is not None
    assert runtime.read_account_header().account_balance.value == Decimal("10000.0")
    assert runtime.read_account_header().available_funds is not None
    assert runtime.read_account_header().available_funds.value == Decimal("9250.5")
    assert runtime.read_account_header().execution_mode == "PAPER"
    assert runtime.read_dashboard().account_profit_loss is not None
    assert runtime.read_dashboard().account_profit_loss.value == Decimal("-249.5")
    assert saved_accounts == ["DEMO-A"]

    controller.switch_account("DEMO-B")
    _wait_until_idle(controller)
    app.processEvents()

    assert adapter.switch_calls == ["DEMO-B"]
    assert runtime.read_account_header().account_id == "DEMO-B"
    assert saved_accounts == ["DEMO-A", "DEMO-B"]

    controller.disconnect()
    assert runtime.active_ig_connection is None
    assert runtime.read_account_header().ig_rest_status == "disconnected"
    assert adapter.logged_out is True


def test_v2_controller_connects_live_with_paper_execution_and_live_profile(tmp_path) -> None:
    app = _application()

    class FakeLiveAdapter(FakeReadOnlyAdapter):
        def login(self, _credentials: IGCredentials) -> IGSession:
            return IGSession(
                cst="fake-live-cst",
                security_token="fake-live-token",
                current_account_id="LIVE-A",
            )

        def get_accounts(self) -> list[Account]:
            return [
                Account(
                    account_id="LIVE-A",
                    account_name="Live CFD",
                    account_type="CFD",
                    currency="EUR",
                    balance=12000.0,
                    available=11000.0,
                    deposit=1000.0,
                    profit_loss=0.0,
                )
            ]

    adapter = FakeLiveAdapter()
    factory_calls: list[IGEnvironment] = []
    credential_store = FakeCredentialStore()
    runtime = TradingRuntime(
        ig_adapter_factory=lambda environment: factory_calls.append(environment) or adapter
    )
    config = _config()
    controller = ReadOnlyConnectionController(
        runtime=runtime,
        config=config,
        config_path=tmp_path / "config.json",
        credential_store=credential_store,
        save_config_fn=lambda _config, _path: None,
    )

    controller.connect_live()
    _wait_until_idle(controller)
    app.processEvents()

    connection = runtime.active_ig_connection
    assert connection is not None
    assert connection.environment is IGEnvironment.LIVE
    assert connection.current_account_id == "LIVE-A"
    assert factory_calls == [IGEnvironment.LIVE]
    assert credential_store.profile_keys == ["live"]
    assert runtime.read_account_header().ig_environment == "live"
    assert runtime.read_account_header().execution_mode == "PAPER"
    assert config.environment is IGEnvironment.LIVE
    assert config.enable_live_trading is False
    assert config.read_only is True

    controller.disconnect()
    assert adapter.logged_out is True


def test_v2_header_exposes_read_only_environment_controls_without_auto(tmp_path) -> None:
    from trading_ig_assistant.ui.shell.main_window_v2 import MainWindowV2

    app = _application()
    adapter = FakeReadOnlyAdapter()
    runtime = TradingRuntime(ig_adapter_factory=lambda _environment: adapter)
    config = _config()
    controller = ReadOnlyConnectionController(
        runtime=runtime,
        config=config,
        config_path=tmp_path / "config.json",
        credential_store=FakeCredentialStore(),
        save_config_fn=lambda _config, _path: None,
    )
    window = MainWindowV2(
        config=config,
        facade=RuntimeUIFacade(runtime),
        connection_controller=controller,
    )
    window.show()
    app.processEvents()

    assert window.account_header.environment_combo.currentData() == "demo"
    assert window.account_header.connect_button.text() == ""
    assert window.account_header.connect_button.icon().isNull() is False
    assert window.account_header.connect_button.accessibleName() == "Connecter"
    assert window.account_header.account_combo.currentText() == (
        "Aucun compte — connectez DEMO ou LIVE"
    )
    assert window.account_header.account_combo.isEnabled() is False
    assert "AUTO" not in window.account_header.safety_label.text()
    assert hasattr(controller, "connect_live")

    window.account_header.connect_button.click()
    _wait_until_idle(controller)
    app.processEvents()

    assert window.account_header.account_combo.count() == 2
    assert "DEMO" in window.account_header.account_combo.currentText()
    assert "CFD" in window.account_header.account_combo.currentText()
    assert "DEMO" in window.account_header.account_label.text()
    assert "CFD" in window.account_header.account_label.text()
    assert "BARRIÈRES & OPTIONS" in window.account_header.account_combo.itemText(1)
    assert window.account_header.balance_card.value.text() == "10000.0 EUR"
    assert window.account_header.available_card.value.text() == "9250.5 EUR"
    assert window.account_header.pnl_card.value.text() == "-249.5 EUR"
    assert window.account_header.pnl_card.value.property("state") == "loss"
    assert window.account_header.connect_button.text() == ""
    assert window.account_header.connect_button.icon().isNull() is False
    assert window.account_header.connect_button.accessibleName() == "Déconnecter"
    assert window.account_header.connect_button.property("connectionState") == "connected"
    assert window.account_header.connect_button.isEnabled()
    assert window.account_header.environment_combo.isEnabled() is False
    assert window.minimumSizeHint().width() <= 1366
    assert window.minimumSizeHint().height() <= 768

    window.account_header.connect_button.click()
    app.processEvents()
    assert adapter.logged_out is True
    assert window.account_header.connect_button.text() == ""

    window.close()
    app.processEvents()


def test_v2_controller_missing_profile_never_constructs_an_adapter(tmp_path) -> None:
    _application()
    factory_calls: list[IGEnvironment] = []
    runtime = TradingRuntime(
        ig_adapter_factory=lambda environment: factory_calls.append(environment)
    )
    errors: list[str] = []
    controller = ReadOnlyConnectionController(
        runtime=runtime,
        config=AppConfig(),
        config_path=tmp_path / "config.json",
        credential_store=FakeCredentialStore(),
    )
    controller.error.connect(errors.append)

    controller.connect_live()

    assert errors == ["connection.profile_missing.live"]
    assert factory_calls == []
    assert runtime.active_ig_connection is None


def test_account_header_labels_environment_and_account_family_for_live_projection() -> None:
    from trading_ig_assistant.app.projections.account_projection import (
        build_account_header_projection,
    )
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.shell.account_header import AccountHeader

    app = _application()
    language = LanguageManager("fr_FR")
    header = AccountHeader(language)
    account = Account(
        account_id="LIVE-OPTIONS-A",
        account_name="Barrières et Options",
        account_type="OPTIONS",
        currency="EUR",
        profit_loss=125.0,
    )
    header.set_accounts((account,), account.account_id)
    header.set_snapshot(
        build_account_header_projection(
            generation_id=1,
            account=account,
            environment="live",
            execution_mode="PAPER",
            open_positions_count=0,
            rest_status="connected",
            stream_status="live",
            ai_status="not_configured",
            generated_at_utc=datetime(2026, 11, 9, 12, 0, tzinfo=UTC),
        )
    )

    assert "LIVE · BARRIÈRES & OPTIONS" in header.account_label.text()
    assert "LIVE · BARRIÈRES & OPTIONS" in header.account_combo.currentText()
    assert header.safety_label.text().startswith("LIVE ·")
    assert header.environment_combo.currentData() == "live"
    assert header.connect_button.text() == ""
    assert header.connect_button.icon().isNull() is False
    assert header.pnl_card.value.text() == "125.0 EUR"
    assert header.pnl_card.value.property("state") == "profit"

    header.close()
    header.deleteLater()
    app.processEvents()
    language.close()


def test_account_metric_refresh_does_not_rebuild_or_flicker_account_combo() -> None:
    from trading_ig_assistant.app.projections.account_projection import (
        build_account_header_projection,
    )
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.shell.account_header import AccountHeader

    app = _application()
    language = LanguageManager("fr_FR")
    header = AccountHeader(language)
    accounts = (
        Account(account_id="LIVE-CFD-A", account_name="Compte CFD", account_type="CFD"),
        Account(
            account_id="LIVE-OPTIONS-A",
            account_name="Barrières et Options",
            account_type="OPTIONS",
        ),
        Account(
            account_id="LIVE-SPREAD-A",
            account_name="Compte Spread Betting",
            account_type="SPREADBET",
        ),
    )
    snapshot = build_account_header_projection(
        generation_id=1,
        account=accounts[2],
        environment="live",
        execution_mode="PAPER",
        open_positions_count=0,
        rest_status="connected",
        stream_status="live",
        ai_status="not_configured",
        generated_at_utc=datetime(2026, 11, 10, 12, 0, tzinfo=UTC),
    )
    header.set_connection_controls_available(True)
    header.set_accounts(accounts, accounts[2].account_id)
    header.set_snapshot(snapshot)
    app.processEvents()

    assert header.account_combo.currentIndex() == 2
    assert "SPREAD BET" in header.account_combo.itemText(2)
    assert "Compte Spread Betting" in header.account_combo.itemText(2)
    model_events: list[str] = []
    model = header.account_combo.model()
    model.rowsInserted.connect(lambda *_args: model_events.append("inserted"))
    model.rowsRemoved.connect(lambda *_args: model_events.append("removed"))

    header.set_snapshot(replace(snapshot, generated_at_utc=datetime.now(UTC)))
    app.processEvents()

    assert model_events == []
    assert header.account_combo.currentIndex() == 2
    assert header.account_combo.isEnabled()

    header.close()
    header.deleteLater()
    app.processEvents()
    language.close()


def test_v2_controller_defers_close_until_connection_worker_finishes(tmp_path) -> None:
    app = _application()
    started = Event()
    release = Event()

    class BlockingAdapter(FakeReadOnlyAdapter):
        def login(self, credentials: IGCredentials) -> IGSession:
            started.set()
            assert release.wait(3)
            return super().login(credentials)

    adapter = BlockingAdapter()
    runtime = TradingRuntime(ig_adapter_factory=lambda _environment: adapter)
    controller = ReadOnlyConnectionController(
        runtime=runtime,
        config=_config(),
        config_path=tmp_path / "config.json",
        credential_store=FakeCredentialStore(),
        save_config_fn=lambda _config, _path: None,
    )
    ready = Event()
    controller.ready_to_close.connect(ready.set)

    controller.connect_demo()
    assert started.wait(1)
    assert controller.close() is False

    release.set()
    _wait_until_idle(controller)
    app.processEvents()

    assert ready.is_set()
    assert runtime.active_ig_connection is None
    assert adapter.logged_out is True
