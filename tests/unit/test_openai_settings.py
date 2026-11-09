import time
from datetime import UTC, datetime, timedelta

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.app.config import AppConfig
from trading_ig_assistant.domain.ai_context import AIAnalysisStatus
from trading_ig_assistant.domain.macro_context import ContextSeverity, ContextSignal
from trading_ig_assistant.services.ai_context_service import build_market_context_snapshot
from trading_ig_assistant.services.macro_context_service import MacroContextService
from trading_ig_assistant.ui.settings_dialog import OpenAISettingsWidget, SettingsDialog


def _available_snapshot():
    now = datetime(2026, 11, 4, 15, 0, tzinfo=UTC)
    signal = ContextSignal(
        signal_id="OPENAI-PROBE-OFFICIAL-CONTEXT",
        label="Synthetic probe",
        severity=ContextSeverity.YELLOW,
        score=None,
        summary="Synthetic validation evidence",
        source="TradingIG validation fixture",
        source_url="https://developers.openai.com/",
        observed_at_utc=now,
        valid_until_utc=now + timedelta(minutes=15),
        confidence=None,
        tags=("validation_only",),
    )
    macro_state = MacroContextService().build_state((signal,), now)

    class Provider:
        model_id = "openai-responses:test-model"

        def analyze(self, _request):
            return {
                "directional_bias": "unknown",
                "event_risk": "medium",
                "confidence": 0.5,
                "summary": "Synthetic response",
                "risk_flags": ["VALIDATION_ONLY"],
                "source_signal_ids": [signal.signal_id],
            }

    return build_market_context_snapshot(
        snapshot_id="OPENAI-PROBE-TEST",
        instrument_id="VALIDATION-ONLY",
        macro_state=macro_state,
        generated_at_utc=now,
        valid_for=timedelta(minutes=10),
        prompt_version="openai-context-probe-v1",
        provider=Provider(),
    )


def test_openai_settings_requires_key_model_and_explicit_acknowledgement() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    widget = OpenAISettingsWidget(api_key_present=False)

    widget.model.setCurrentText("gpt-6-luna")
    widget.acknowledgement.setChecked(True)
    assert not widget.periodic_refresh.isChecked()
    assert not widget.test_button.isEnabled()
    assert "ABSENTE" in widget.key_status.text()

    requested = []
    widget.test_requested.connect(lambda model, cap: requested.append((model, cap)))
    widget.set_key_present(True)
    assert widget.test_button.isEnabled()
    widget.test_button.click()

    assert requested == [("gpt-6-luna", 600)]
    assert "DÉTECTÉE" in widget.key_status.text()


def test_settings_dialog_runs_openai_probe_without_blocking_qt_or_showing_secret() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    calls = []

    def runner(*, model, api_key, max_output_tokens):
        calls.append((model, api_key, max_output_tokens))
        time.sleep(0.08)
        return _available_snapshot()

    dialog = SettingsDialog(
        AppConfig(),
        None,
        openai_probe_runner=runner,
        openai_key_reader=lambda: "test-secret-never-rendered",
    )
    dialog.openai_settings.model.setCurrentText("gpt-6-luna")
    dialog.openai_settings.acknowledgement.setChecked(True)
    dialog.openai_settings.periodic_refresh.setChecked(True)
    runtime_validations = []
    dialog.openai_runtime_validated.connect(
        lambda model, cap, periodic: runtime_validations.append((model, cap, periodic))
    )
    dialog.show()

    ticks = []
    timer = QtCore.QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start()
    dialog.openai_settings.test_button.click()
    deadline = time.monotonic() + 2.0
    while dialog._openai_thread is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.002)
    timer.stop()
    app.processEvents()

    assert dialog._openai_thread is None
    assert len(ticks) >= 2
    assert len(calls) == 1
    assert calls[0][0] == "gpt-6-luna"
    assert isinstance(calls[0][1], SecretValue)
    assert calls[0][2] == 600
    assert "Connexion validée" in dialog.openai_settings.result.text()
    assert "test-secret-never-rendered" not in dialog.openai_settings.result.text()
    assert runtime_validations == [("gpt-6-luna", 600, True)]
    assert "toutes les 15 minutes" in dialog.openai_settings.result.text()
    assert _available_snapshot().ai_analysis.status is AIAnalysisStatus.AVAILABLE
    dialog.close()
    app.processEvents()
