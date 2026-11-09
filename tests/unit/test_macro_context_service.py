from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_ig_assistant.domain.macro_context import (
    ContextSeverity,
    ContextSignal,
    DirectionalBias,
    EventRisk,
    MarketRegime,
)
from trading_ig_assistant.services.macro_context_service import MacroContextService
from trading_ig_assistant.services.macro_ribbon_service import MacroRibbonService

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)


def _signal(
    signal_id: str,
    score: str,
    severity: ContextSeverity,
    tags: tuple[str, ...],
    *,
    valid_until: datetime | None = None,
) -> ContextSignal:
    return ContextSignal(
        signal_id=signal_id,
        label=signal_id,
        severity=severity,
        score=Decimal(score),
        summary=f"Summary for {signal_id}",
        source="fixture-provider",
        source_url=f"https://example.invalid/{signal_id}",
        observed_at_utc=NOW - timedelta(minutes=5),
        valid_until_utc=valid_until or NOW + timedelta(hours=1),
        confidence=Decimal("0.8"),
        tags=tags,
    )


def test_context_aggregation_preserves_sources_and_direction() -> None:
    state = MacroContextService().build_state(
        (
            _signal("risk", "50", ContextSeverity.GREEN, ("risk",)),
            _signal("index", "50", ContextSeverity.GREEN, ("index",)),
            _signal("gold", "-50", ContextSeverity.YELLOW, ("gold",)),
            _signal("event", "0", ContextSeverity.RED, ("event",)),
        ),
        NOW,
    )

    assert state.regime is MarketRegime.RISK_ON
    assert state.index_bias is DirectionalBias.BULLISH
    assert state.gold_bias is DirectionalBias.BEARISH
    assert state.event_risk is EventRisk.HIGH
    assert "source:fixture-provider" in state.provenance
    assert state.signals[0].signal_id == "event"


def test_stale_signal_degrades_to_gray_and_unknown() -> None:
    state = MacroContextService().build_state(
        (
            _signal(
                "old-event",
                "100",
                ContextSeverity.RED,
                ("event",),
                valid_until=NOW - timedelta(seconds=1),
            ),
        ),
        NOW,
    )

    assert state.signals[0].severity is ContextSeverity.GRAY
    assert state.signals[0].score is None
    assert state.event_risk is EventRisk.UNKNOWN
    assert "STALE:old-event" in state.reason_codes


def test_future_or_expiring_now_signals_do_not_drive_market_context() -> None:
    from dataclasses import replace

    future = replace(
        _signal("future", "100", ContextSeverity.GREEN, ("index",)),
        observed_at_utc=NOW + timedelta(seconds=1),
    )
    expired = _signal("expiry", "100", ContextSeverity.RED, ("event",), valid_until=NOW)
    state = MacroContextService().build_state((future, expired), NOW)
    assert state.index_bias is DirectionalBias.UNKNOWN
    assert state.event_risk is EventRisk.UNKNOWN
    assert "FUTURE:future" in state.reason_codes
    assert "STALE:expiry" in state.reason_codes


def test_stored_macro_aggregate_is_revalidated_before_later_consumption() -> None:
    service = MacroContextService()
    signal = _signal(
        "event", "0", ContextSeverity.GREEN, ("event",), valid_until=NOW + timedelta(seconds=1)
    )
    state = service.build_state((signal,), NOW)
    assert state.event_risk is EventRisk.LOW
    assert service.revalidate_state(state, NOW) is state
    expired = service.revalidate_state(state, NOW + timedelta(seconds=1))
    assert expired.event_risk is EventRisk.UNKNOWN
    assert "STALE:event" in expired.reason_codes
    future = service.revalidate_state(state, NOW - timedelta(seconds=1))
    assert future.event_risk is EventRisk.UNKNOWN
    assert "CONTEXT_FROM_FUTURE" in future.reason_codes


def test_missing_context_remains_unknown() -> None:
    state = MacroContextService().build_state((), NOW)

    assert state.regime is MarketRegime.UNKNOWN
    assert state.index_bias is DirectionalBias.UNKNOWN
    assert state.gold_bias is DirectionalBias.UNKNOWN
    assert state.event_risk is EventRisk.UNKNOWN
    assert state.reason_codes[0] == "NO_CONTEXT"
    assert state.provenance == ()


def test_ribbon_projection_keeps_gray_unknown_state_visible() -> None:
    state = MacroContextService().build_state((), NOW)

    indicators = MacroRibbonService().project(state)

    assert len(indicators) == 4
    assert all(indicator.severity is ContextSeverity.GRAY for indicator in indicators)


def test_qt_ribbon_consumes_normalized_state_with_accessible_text() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui.macro_ribbon_widget import MacroRibbonWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    state = MacroContextService().build_state(
        (_signal("event", "0", ContextSeverity.RED, ("event",)),),
        NOW,
    )
    widget = MacroRibbonWidget()

    widget.set_state(state)
    app.processEvents()

    texts = [label.text() for label in widget._labels]
    assert "Event risk: high [RED]" in texts
    event_label = next(label for label in widget._labels if label.text().startswith("event:"))
    assert "Source: fixture-provider" in event_label.toolTip()
    assert "status red" in event_label.accessibleName()
    widget.close()


def test_qt_ribbon_exposes_safe_ai_unavailable_diagnostic() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.ai_context import AIAnalysisStatus, MarketAIAnalysis
    from trading_ig_assistant.domain.macro_context import DirectionalBias, EventRisk
    from trading_ig_assistant.ui.macro_ribbon_widget import MacroRibbonWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    analysis = MarketAIAnalysis(
        status=AIAnalysisStatus.UNAVAILABLE,
        model_id="openai-responses:test-model",
        prompt_version="test-v1",
        market_scope="GLOBAL-MARKET-CONTEXT",
        directional_bias=DirectionalBias.UNKNOWN,
        event_risk=EventRisk.UNKNOWN,
        confidence=None,
        summary="AI context unavailable",
        risk_flags=(),
        source_signal_ids=(),
        generated_at_utc=NOW,
        valid_until_utc=NOW + timedelta(minutes=10),
    )
    widget = MacroRibbonWidget()

    widget.set_ai_analysis(analysis, ("AI_OUTPUT_INVALID",))
    app.processEvents()

    ai_label = next(label for label in widget._labels if label.text().startswith("AI:"))
    assert "AI: unavailable [GRAY]" == ai_label.text()
    assert "Diagnostic sûr: AI_OUTPUT_INVALID" in ai_label.toolTip()
    widget.close()
