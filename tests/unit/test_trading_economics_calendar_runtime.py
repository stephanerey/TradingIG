import json
import time
from datetime import UTC, datetime, timedelta

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.adapters.trading_economics_calendar import CalendarHttpResponse
from trading_ig_assistant.app.config import AppConfig
from trading_ig_assistant.domain.context_sources import ProviderCollectionStatus
from trading_ig_assistant.domain.macro_context import ContextSeverity
from trading_ig_assistant.services.trading_economics_calendar_runtime import (
    TradingEconomicsRuntimeConfig,
    TradingEconomicsRuntimeResult,
    refresh_trading_economics_calendar,
)
from trading_ig_assistant.ui.settings_dialog import (
    SettingsDialog,
    TradingEconomicsSettingsWidget,
)

NOW = datetime(2026, 11, 5, 10, 0, tzinfo=UTC)
SECRET = "synthetic-calendar-secret"


def _payload() -> list[dict[str, object]]:
    return [
        {
            "CalendarId": "HIGH-1",
            "Date": "2026-11-05T10:30:00",
            "Country": "United States",
            "Category": "Inflation Rate",
            "Event": "Synthetic CPI",
            "Source": "Official Statistical Agency",
            "SourceURL": "https://official.example/cpi",
            "DateSpan": "0",
            "Importance": 3,
        }
    ]


def _runtime_result(*, now: datetime = NOW) -> TradingEconomicsRuntimeResult:
    def transport(url, _headers, _timeout, _max_bytes):
        return CalendarHttpResponse(
            body=json.dumps(_payload()).encode(),
            final_url=url,
            content_type="application/json",
        )

    return refresh_trading_economics_calendar(
        api_key=SecretValue(SECRET),
        config=TradingEconomicsRuntimeConfig(countries=("united states",)),
        transport=transport,
        clock=lambda: now,
    )


def test_runtime_projects_available_health_and_conservative_event_risk() -> None:
    result = _runtime_result()

    assert result.snapshot.status is ProviderCollectionStatus.AVAILABLE
    assert len(result.snapshot.events) == 1
    assert result.signals[0].signal_id == "economic-calendar-source-health"
    assert result.signals[0].severity is ContextSeverity.GREEN
    assert result.signals[1].signal_id.endswith("trading-economics:HIGH-1")
    assert result.signals[1].severity is ContextSeverity.GRAY
    assert result.signals[1].score is None
    assert "rights:unknown" in result.signals[1].tags


def test_runtime_degrades_transport_failure_without_exposing_secret() -> None:
    def transport(*_args):
        raise RuntimeError(SECRET)

    result = refresh_trading_economics_calendar(
        api_key=SecretValue(SECRET),
        config=TradingEconomicsRuntimeConfig(countries=("united states",)),
        transport=transport,
        clock=lambda: NOW,
    )

    assert result.snapshot.status is ProviderCollectionStatus.UNAVAILABLE
    assert result.snapshot.reason_codes == ("CALENDAR_PROVIDER_ERROR",)
    assert len(result.signals) == 1
    assert result.signals[0].severity is ContextSeverity.GRAY
    assert SECRET not in repr(result)


def test_calendar_settings_require_key_countries_and_explicit_acknowledgement() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    widget = TradingEconomicsSettingsWidget(api_key_present=False)
    widget.acknowledgement.setChecked(True)
    assert not widget.test_button.isEnabled()
    assert "ABSENTE" in widget.key_status.text()

    requests = []
    widget.test_requested.connect(requests.append)
    widget.set_key_present(True)
    assert widget.test_button.isEnabled()
    widget.test_button.click()

    assert len(requests) == 1
    assert requests[0].countries == ("united states", "euro area")
    assert requests[0].lookahead == timedelta(hours=48)


def test_settings_dialog_runs_calendar_probe_outside_qt_and_hides_secret() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    calls = []

    def runner(*, api_key, config):
        calls.append((api_key, config))
        time.sleep(0.08)
        return _runtime_result()

    dialog = SettingsDialog(
        AppConfig(),
        None,
        calendar_probe_runner=runner,
        calendar_key_reader=lambda: SECRET,
    )
    dialog.calendar_settings.acknowledgement.setChecked(True)
    validated = []
    dialog.calendar_runtime_validated.connect(validated.append)
    dialog.show()

    ticks = []
    timer = QtCore.QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start()
    dialog.calendar_settings.test_button.click()
    deadline = time.monotonic() + 2.0
    while dialog._calendar_thread is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.002)
    timer.stop()
    app.processEvents()

    assert dialog._calendar_thread is None
    assert len(ticks) >= 2
    assert len(calls) == 1
    assert isinstance(calls[0][0], SecretValue)
    assert len(validated) == 1
    assert "Connexion validée" in dialog.calendar_settings.result.text()
    assert SECRET not in dialog.calendar_settings.result.text()
    dialog.close()
    app.processEvents()


def test_main_window_composes_calendar_with_official_news_and_refreshes_in_worker() -> None:
    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    class NewsProvider:
        provider_id = "offline-official-provider"

        def fetch_news(self, *, as_of_utc):
            assert as_of_utc.tzinfo is UTC
            return ()

    calls = []

    def runner(*, api_key, config):
        calls.append((api_key, config))
        return _runtime_result(now=datetime.now(UTC))

    window = MainWindow(
        official_news_providers=(NewsProvider(),),
        official_news_refresh_interval_ms=60_000,
        calendar_context_runner=runner,
        calendar_key_reader=lambda: SECRET,
        calendar_refresh_interval_ms=60_000,
    )
    deadline = time.monotonic() + 2.0
    while (
        window._official_news_thread is not None or not window._latest_news_snapshots
    ) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)

    calendar_now = max(
        snapshot.collected_at_utc for snapshot in window._latest_news_snapshots
    )
    window._enable_calendar_context_session(_runtime_result(now=calendar_now))
    labels = [label.text() for label in window.macro_ribbon._labels]
    assert any("Official news sources: green" in label for label in labels)
    assert any("Economic calendar source: green" in label for label in labels)
    assert "Event risk: unknown [GRAY]" in labels
    assert window._calendar_context_action.isEnabled()

    window._calendar_context_action.trigger()
    deadline = time.monotonic() + 2.0
    while window._calendar_context_thread is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert len(calls) == 1
    assert isinstance(calls[0][0], SecretValue)
    window.close()
    app.processEvents()
