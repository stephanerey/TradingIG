import time
from datetime import timedelta

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.domain.context_sources import (
    ContextCategory,
    ContextImportance,
    NewsItem,
    SourceUsageRights,
)
from trading_ig_assistant.services.ai_context_service import build_market_context_snapshot


def test_expired_news_does_not_enable_or_start_openai_context() -> None:
    from dataclasses import replace
    from datetime import UTC, datetime

    from trading_ig_assistant.domain.macro_context import ContextSeverity, ContextSignal
    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow(openai_key_reader=lambda: "runtime-test-secret")
    now = datetime.now(UTC)
    expired = ContextSignal(
        signal_id="news:expired",
        label="Expired",
        severity=ContextSeverity.GRAY,
        score=None,
        summary="Old collection",
        source="synthetic",
        source_url=None,
        observed_at_utc=now - timedelta(minutes=20),
        valid_until_utc=now - timedelta(minutes=1),
        confidence=None,
        tags=("ai_evidence",),
    )
    window._latest_macro_state = replace(window._latest_macro_state, signals=(expired,))
    window._enable_openai_context_session("test-model", 600)
    assert not window._has_openai_evidence()
    assert not window._openai_context_action.isEnabled()
    window._refresh_openai_context()
    assert window._openai_context_thread is None
    assert "Aucune métadonnée" in window.statusBar().currentMessage()
    window.close()


def test_ai_ribbon_degrades_on_scope_change_and_expiry_without_provider_call() -> None:
    from datetime import UTC, datetime
    from decimal import Decimal

    from trading_ig_assistant.domain.ai_context import (
        AIAnalysisStatus,
        MarketAIAnalysis,
        MarketContextSnapshot,
    )
    from trading_ig_assistant.domain.macro_context import DirectionalBias, EventRisk
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.services.macro_context_service import MacroContextService
    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    calls = []
    window = MainWindow(openai_context_runner=lambda **kwargs: calls.append(kwargs))
    now = datetime.now(UTC)
    macro = MacroContextService().build_state((), now)
    analysis = MarketAIAnalysis(
        status=AIAnalysisStatus.AVAILABLE,
        model_id="fixture",
        prompt_version="v1",
        market_scope="EPIC.A",
        directional_bias=DirectionalBias.BULLISH,
        event_risk=EventRisk.LOW,
        confidence=Decimal("0.8"),
        summary="Fixture",
        risk_flags=(),
        source_signal_ids=("fixture",),
        generated_at_utc=now,
        valid_until_utc=now + timedelta(seconds=5),
    )
    snapshot = MarketContextSnapshot(
        schema_version=1,
        snapshot_id="S",
        instrument_id="EPIC.A",
        macro_state=macro,
        ai_analysis=analysis,
        generated_at_utc=now,
        valid_until_utc=now + timedelta(seconds=1),
        reason_codes=(),
        provenance=(),
    )
    window._selected_product = TradableProduct(
        epic="EPIC.A", name="A", product_type=ProductType.CASH_OR_DFB
    )
    window._on_openai_context_success(snapshot)
    assert window.macro_ribbon._ai_chip.value == "bullish / risk low"
    window._selected_product = TradableProduct(
        epic="EPIC.B", name="B", product_type=ProductType.CASH_OR_DFB
    )
    window._refresh_ai_presentation()
    assert window.macro_ribbon._ai_chip.value == "not-applicable"
    window._selected_product = TradableProduct(
        epic="EPIC.A", name="A", product_type=ProductType.CASH_OR_DFB
    )
    window._refresh_ai_presentation()
    deadline = time.monotonic() + 3
    while window.macro_ribbon._ai_chip.value != "stale" and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert window.macro_ribbon._ai_chip.value == "stale"
    assert calls == []
    window.close()


def test_main_window_openai_context_is_session_gated_manual_and_non_blocking() -> None:
    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    calls = []

    class OfficialProvider:
        provider_id = "official-runtime-fixture"

        def fetch_news(self, *, as_of_utc):
            return (
                NewsItem(
                    schema_version=1,
                    item_id="runtime-news-1",
                    headline="Official runtime headline",
                    summary=None,
                    category=ContextCategory.CENTRAL_BANK,
                    importance=ContextImportance.UNKNOWN,
                    published_at_utc=as_of_utc - timedelta(minutes=1),
                    observed_at_utc=as_of_utc,
                    source="Official runtime source",
                    source_url="https://official.example/runtime-news-1",
                    usage_rights=SourceUsageRights.METADATA_ONLY,
                    tags=("official",),
                ),
            )

    def context_runner(*, model, api_key, max_output_tokens, macro_state, instrument_id):
        calls.append((model, repr(api_key), max_output_tokens, macro_state, instrument_id))
        time.sleep(0.08)
        evidence_id = next(
            signal.signal_id for signal in macro_state.signals if "ai_evidence" in signal.tags
        )

        class Provider:
            model_id = f"openai-responses:{model}"

            def analyze(self, _request):
                return {
                    "directional_bias": "unknown",
                    "event_risk": "medium",
                    "confidence": 0.5,
                    "summary": "Consultative fixture analysis",
                    "risk_flags": ["NEWS_CONTEXT"],
                    "source_signal_ids": [evidence_id],
                }

        return build_market_context_snapshot(
            snapshot_id="RUNTIME-CONTEXT-1",
            instrument_id=instrument_id,
            macro_state=macro_state,
            generated_at_utc=macro_state.generated_at_utc,
            valid_for=timedelta(minutes=10),
            prompt_version="openai-market-context-v1",
            provider=Provider(),
        )

    window = MainWindow(
        official_news_providers=(OfficialProvider(),),
        official_news_refresh_interval_ms=60_000,
        openai_context_runner=context_runner,
        openai_key_reader=lambda: "runtime-test-secret",
    )
    deadline = time.monotonic() + 2.0
    while (
        window._official_news_thread is not None
        or not any("ai_evidence" in signal.tags for signal in window._latest_macro_state.signals)
    ) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.002)

    assert calls == []
    assert not window._openai_context_action.isEnabled()
    window._enable_openai_context_session("test-model", 600)
    assert window._openai_context_action.isEnabled()
    assert not window._openai_context_refresh_timer.isActive()

    ticks = []
    timer = QtCore.QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start()
    window._openai_context_action.trigger()
    deadline = time.monotonic() + 2.0
    while window._openai_context_thread is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.002)
    timer.stop()
    app.processEvents()

    assert window._openai_context_thread is None
    assert len(ticks) >= 2
    assert len(calls) == 1
    assert calls[0][0:3] == ("test-model", "***REDACTED***", 600)
    expected_scope = (
        window._selected_product.epic
        if window._selected_product is not None
        else "GLOBAL-MARKET-CONTEXT"
    )
    assert calls[0][4] == expected_scope
    assert window._openai_context_action.isEnabled()
    assert any(
        "AI: unknown / risk medium [YELLOW]" in label.text()
        for label in window.macro_ribbon._labels
    )
    assert window.paper_portfolio.positions_table.rowCount() == 0
    assert window.paper_portfolio.orders_table.rowCount() == 0
    window.close()
    app.processEvents()


def test_periodic_openai_context_requires_opt_in_and_skips_overlapping_calls() -> None:
    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    calls = []

    class OfficialProvider:
        provider_id = "official-periodic-fixture"

        def fetch_news(self, *, as_of_utc):
            return (
                NewsItem(
                    schema_version=1,
                    item_id="periodic-news-1",
                    headline="Official periodic headline",
                    summary=None,
                    category=ContextCategory.CENTRAL_BANK,
                    importance=ContextImportance.UNKNOWN,
                    published_at_utc=as_of_utc - timedelta(minutes=1),
                    observed_at_utc=as_of_utc,
                    source="Official periodic source",
                    source_url="https://official.example/periodic-news-1",
                    usage_rights=SourceUsageRights.METADATA_ONLY,
                    tags=("official",),
                ),
            )

    def context_runner(*, model, api_key, max_output_tokens, macro_state, instrument_id):
        calls.append((model, repr(api_key), max_output_tokens, macro_state, instrument_id))
        time.sleep(0.08)
        evidence_id = next(
            signal.signal_id for signal in macro_state.signals if "ai_evidence" in signal.tags
        )

        class Provider:
            model_id = f"openai-responses:{model}"

            def analyze(self, _request):
                return {
                    "directional_bias": "unknown",
                    "event_risk": "unknown",
                    "confidence": None,
                    "summary": "Periodic consultative fixture",
                    "risk_flags": ["PERIODIC_CONTEXT"],
                    "source_signal_ids": [evidence_id],
                }

        return build_market_context_snapshot(
            snapshot_id="RUNTIME-PERIODIC-1",
            instrument_id=instrument_id,
            macro_state=macro_state,
            generated_at_utc=macro_state.generated_at_utc,
            valid_for=timedelta(minutes=10),
            prompt_version="openai-market-context-v1",
            provider=Provider(),
        )

    window = MainWindow(
        official_news_providers=(OfficialProvider(),),
        official_news_refresh_interval_ms=60_000,
        openai_context_runner=context_runner,
        openai_key_reader=lambda: "runtime-test-secret",
        openai_context_refresh_interval_ms=15 * 60 * 1000,
    )
    deadline = time.monotonic() + 2.0
    while (
        window._official_news_thread is not None
        or not any("ai_evidence" in signal.tags for signal in window._latest_macro_state.signals)
    ) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.002)

    window._enable_openai_context_session("test-model", 600, True)
    assert window._openai_context_refresh_timer.isActive()
    assert window._openai_context_refresh_timer.interval() == 15 * 60 * 1000
    assert calls == []

    window._openai_context_refresh_timer.timeout.emit()
    deadline = time.monotonic() + 1.0
    while not calls and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.002)
    assert len(calls) == 1
    window._openai_context_refresh_timer.timeout.emit()
    app.processEvents()
    assert len(calls) == 1
    assert calls[0][0:3] == ("test-model", "***REDACTED***", 600)
    assert window.paper_portfolio.positions_table.rowCount() == 0
    assert window.paper_portfolio.orders_table.rowCount() == 0

    window._openai_context_refresh_timer.stop()
    deadline = time.monotonic() + 2.0
    while window._openai_context_thread is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.002)
    window.close()
    app.processEvents()
