from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.app.projections.common import Availability
from trading_ig_assistant.app.projections.macro_projection import build_macro_projection
from trading_ig_assistant.app.qt_macro_context_controller import MacroContextController
from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
from trading_ig_assistant.domain.ai_context import (
    AIAnalysisStatus,
    MarketAIAnalysis,
    MarketContextSnapshot,
)
from trading_ig_assistant.domain.context_sources import (
    ContextCategory,
    ContextImportance,
    NewsCollectionSnapshot,
    NewsItem,
    ProviderCollectionStatus,
    SourceUsageRights,
)
from trading_ig_assistant.domain.macro_context import (
    DirectionalBias,
    EventRisk,
    MacroRibbonState,
)

NOW = datetime(2026, 11, 9, 19, 0, tzinfo=UTC)


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _item() -> NewsItem:
    return NewsItem(
        schema_version=1,
        item_id="FED-1",
        headline="Federal Reserve publishes official statement",
        summary=None,
        category=ContextCategory.CENTRAL_BANK,
        importance=ContextImportance.HIGH,
        published_at_utc=NOW,
        observed_at_utc=NOW,
        source="Federal Reserve",
        source_url="https://www.federalreserve.gov/example",
        usage_rights=SourceUsageRights.METADATA_ONLY,
        tags=("fed",),
    )


def _snapshot() -> NewsCollectionSnapshot:
    return NewsCollectionSnapshot(
        schema_version=1,
        provider_id="fed-test",
        status=ProviderCollectionStatus.AVAILABLE,
        items=(_item(),),
        collected_at_utc=NOW,
        reason_codes=(),
    )


class FakeProvider:
    provider_id = "fed-test"

    def __init__(self) -> None:
        self.calls = 0

    def fetch_news(self, *, as_of_utc: datetime) -> tuple[NewsItem, ...]:
        self.calls += 1
        assert as_of_utc == NOW
        return (_item(),)


def _wait_until_idle(controller: MacroContextController) -> None:
    if not controller.busy:
        return
    loop = QtCore.QEventLoop()
    controller.busy_changed.connect(lambda busy: loop.quit() if not busy else None)
    controller.ai_busy_changed.connect(lambda busy: loop.quit() if not busy else None)
    QtCore.QTimer.singleShot(3000, loop.quit)
    loop.exec()
    assert controller.busy is False


def _ai_runner(**kwargs: object) -> MarketContextSnapshot:
    macro_state = kwargs["macro_state"]
    assert isinstance(macro_state, MacroRibbonState)
    signal = macro_state.signals[0]
    analysis = MarketAIAnalysis(
        status=AIAnalysisStatus.AVAILABLE,
        model_id=f"openai-responses:{kwargs['model']}",
        prompt_version=f"openai-market-context-v2-{kwargs['response_language']}",
        market_scope=str(kwargs["instrument_id"]),
        directional_bias=DirectionalBias.NEUTRAL,
        event_risk=EventRisk.MEDIUM,
        confidence=Decimal("0.62"),
        summary="Official metadata suggests a neutral, cautious context.",
        risk_flags=("EVENT_UNCERTAINTY",),
        source_signal_ids=(signal.signal_id,),
        generated_at_utc=NOW,
        valid_until_utc=NOW + timedelta(minutes=10),
    )
    return MarketContextSnapshot(
        schema_version=1,
        snapshot_id="AI-1",
        instrument_id=str(kwargs["instrument_id"]),
        macro_state=macro_state,
        ai_analysis=analysis,
        generated_at_utc=NOW,
        valid_until_utc=NOW + timedelta(minutes=10),
        reason_codes=(),
        provenance=("test",),
    )


def test_macro_projection_keeps_official_metadata_and_rights_explicit() -> None:
    projection = build_macro_projection(
        generation_id=2,
        snapshots=(_snapshot(),),
        generated_at_utc=NOW,
    )

    assert projection.news_status is Availability.READY
    assert projection.news_provider_count == 1
    assert len(projection.news_rows) == 1
    assert projection.news_rows[0].usage_rights == "metadata_only"
    assert projection.news_rows[0].importance == "high"
    assert projection.calendar_status is Availability.UNAVAILABLE
    assert projection.news_collected_at_utc == NOW


def test_macro_compact_bar_projects_attested_coverage_and_ai_context() -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.shell.macro_compact_bar import MacroCompactBar

    app = _application()
    language = LanguageManager("fr_FR")
    bar = MacroCompactBar(language)
    coverage = build_macro_projection(
        generation_id=0,
        snapshots=(_snapshot(),),
        generated_at_utc=NOW,
    )

    bar.set_snapshot(coverage)
    app.processEvents()
    assert "Veille disponible" in bar.value_label.text()
    assert "1 actualité" in bar.value_label.text()
    assert "aucune exécution" in bar.value_label.toolTip()

    ready = replace(
        coverage,
        ai_status=Availability.READY,
        ai_model_id="openai-responses:gpt-6-luna",
        ai_prompt_version="test-v1",
        ai_scope="GLOBAL-MARKET-CONTEXT",
        ai_summary="WAIT because the evidence is mixed.",
        ai_directional_bias="unknown",
        ai_event_risk="medium",
        ai_confidence=Decimal("0.22"),
        ai_risk_flags=("WAIT_INSUFFICIENT_EVIDENCE",),
        ai_source_signal_ids=("news:FED-1",),
        ai_generated_at_utc=NOW,
        ai_valid_until_utc=NOW + timedelta(minutes=10),
        ai_reason_codes=(),
    )
    bar.set_snapshot(ready)

    assert "Biais UNKNOWN" in bar.value_label.text()
    assert "confiance 22%" in bar.value_label.text()
    assert "WAIT because the evidence is mixed" in bar.value_label.toolTip()
    language.set_locale("en_US")
    bar.retranslate_ui()
    assert "Bias UNKNOWN" in bar.value_label.text()

    bar.close()
    language.close()


def test_news_controller_never_fetches_until_explicit_refresh() -> None:
    app = _application()
    provider = FakeProvider()
    runtime = TradingRuntime(now_provider=lambda: NOW)
    controller = MacroContextController(
        runtime=runtime,
        providers=(provider,),
        now_provider=lambda: NOW,
    )

    controller.publish_current()
    assert provider.calls == 0
    assert runtime.read_macro().news_rows == ()

    controller.refresh_news()
    _wait_until_idle(controller)
    app.processEvents()

    assert provider.calls == 1
    assert runtime.read_macro().news_rows[0].headline.startswith("Federal Reserve")
    health = {item.service_id: item for item in runtime.read_health()}
    assert health["official-news"].status is Availability.READY


def test_ai_controller_requires_explicit_news_and_request_then_publishes_result() -> None:
    app = _application()
    provider = FakeProvider()
    calls: list[dict[str, object]] = []

    def runner(**kwargs: object) -> MarketContextSnapshot:
        calls.append(kwargs)
        return _ai_runner(**kwargs)

    runtime = TradingRuntime(now_provider=lambda: NOW)
    controller = MacroContextController(
        runtime=runtime,
        providers=(provider,),
        now_provider=lambda: NOW,
        openai_key_reader=lambda: "test-secret-never-rendered",
        ai_runner=runner,
    )
    errors: list[str] = []
    controller.error.connect(errors.append)

    controller.run_ai_analysis("gpt-6-luna", 600, "fr_FR")
    assert errors == ["macro.ai_news_required"]
    assert calls == []

    controller.refresh_news()
    _wait_until_idle(controller)
    controller.run_ai_analysis("gpt-6-luna", 600, "fr_FR")
    _wait_until_idle(controller)
    app.processEvents()

    projection = runtime.read_macro()
    assert len(calls) == 1
    assert calls[0]["response_language"] == "fr"
    assert projection.ai_status is Availability.READY
    assert projection.ai_model_id == "openai-responses:gpt-6-luna"
    assert projection.ai_summary is not None
    assert projection.ai_source_signal_ids == ("news:FED-1",)
    published_context = runtime.read_market_context()
    assert published_context is not None
    assert published_context.snapshot_id == "AI-1"
    assert runtime.read_account_header().ai_status == "ready"
    health = {item.service_id: item for item in runtime.read_health()}
    assert health["openai"].status is Availability.READY

    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.macro_page import MacroPage

    language = LanguageManager("fr_FR")
    page = MacroPage(language)
    assert page.ai_analysis_splitter.orientation() == QtCore.Qt.Vertical
    assert page.ai_analysis_splitter.childrenCollapsible() is False
    page.set_ai_key_present(True)
    later_projection = replace(
        projection,
        generated_at_utc=NOW + timedelta(minutes=1),
    )
    page.set_snapshot(later_projection)
    assert "Source officielle" in page.ai_details.toPlainText()
    assert "Federal Reserve" in page.ai_details.toPlainText()
    assert "news:FED-1" not in page.ai_details.toPlainText()
    assert "précède la dernière collecte" not in page._messages[3].text()
    page.set_snapshot(
        replace(
            later_projection,
            news_collected_at_utc=NOW + timedelta(seconds=30),
        )
    )
    assert "précède la dernière collecte" in page._messages[3].text()
    page.close()
    language.close()

    controller.refresh_news()
    _wait_until_idle(controller)
    assert runtime.read_market_context() is None

    old_generation = runtime.generation_id
    assert runtime.publish_market_context(
        generation_id=old_generation,
        snapshot=published_context,
    )
    runtime.begin_generation()
    assert runtime.read_market_context() is None
    assert (
        runtime.publish_market_context(
            generation_id=old_generation,
            snapshot=published_context,
        )
        is False
    )


def test_macro_page_requires_visible_consent_before_emitting_manual_ai_request() -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.macro_page import MacroPage

    app = _application()
    language = LanguageManager("fr_FR")
    page = MacroPage(language)
    page.set_snapshot(
        build_macro_projection(
            generation_id=0,
            snapshots=(_snapshot(),),
            generated_at_utc=NOW,
        )
    )
    page.set_ai_key_present(True)
    requests: list[bool] = []
    ai_requests: list[tuple[str, int, str]] = []
    page.news_refresh_requested.connect(lambda: requests.append(True))
    page.ai_analysis_requested.connect(
        lambda model, tokens, locale: ai_requests.append((model, tokens, locale))
    )
    page.show()
    app.processEvents()

    assert page.news_table.rowCount() == 1
    assert page.news_table.item(0, 1).text() == "Federal Reserve"
    assert "Aucun sentiment" in page._messages[0].text()
    assert "Analyse prête" in page._messages[3].text()
    assert page.ai_run_button.isEnabled() is False
    page.ai_consent.setChecked(True)
    assert page.ai_run_button.isEnabled() is True
    page.ai_run_button.click()
    assert ai_requests == [("gpt-6-luna", 1_000, "fr_FR")]
    assert page.ai_consent.isChecked() is False
    page.news_refresh_button.click()
    assert requests == [True]

    page.close()
    language.close()


def test_macro_page_distinguishes_selected_evidence_from_completed_result() -> None:
    from trading_ig_assistant.app.projections.macro import AIEvidenceRowVM
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.macro_page import MacroPage

    app = _application()
    projection = build_macro_projection(
        generation_id=0,
        snapshots=(_snapshot(),),
        generated_at_utc=NOW,
    )
    evidence = AIEvidenceRowVM(
        signal_id="news:FED-1",
        headline="Federal Reserve publishes official statement",
        source="Federal Reserve",
        source_url="https://www.federalreserve.gov/example",
        excerpt="A deliberately long excerpt used to verify bounded row rendering.",
        content_origin="short_content",
        published_at_utc=NOW,
    )
    language = LanguageManager("fr_FR")
    page = MacroPage(language)
    page.set_ai_key_present(True)
    page.set_snapshot(replace(projection, ai_evidence_rows=(evidence,)))
    app.processEvents()

    assert "présélectionnés" in page.ai_evidence_label.text()
    assert "Aucune analyse IA" in page.ai_details.toPlainText()
    assert page.ai_evidence_table.rowHeight(0) == 62
    assert page.ai_evidence_table.item(0, 3).toolTip() == evidence.excerpt

    completed = replace(
        projection,
        ai_status=Availability.READY,
        ai_model_id="openai-responses:gpt-6-luna",
        ai_prompt_version="test-v1",
        ai_scope="GLOBAL-MARKET-CONTEXT",
        ai_summary="WAIT because evidence is insufficient.",
        ai_directional_bias="unknown",
        ai_event_risk="unknown",
        ai_confidence=Decimal("0.22"),
        ai_source_signal_ids=("news:FED-1",),
        ai_generated_at_utc=NOW,
        ai_valid_until_utc=NOW + timedelta(minutes=10),
        ai_reason_codes=(),
        ai_evidence_rows=(evidence,),
    )
    page.set_snapshot(completed)

    assert "effectivement utilisés" in page.ai_evidence_label.text()
    assert "WAIT because evidence is insufficient" in page.ai_details.toPlainText()

    page.close()
    language.close()


def test_macro_page_keeps_an_unavailable_attempt_visible_and_recommends_wait() -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.macro_page import MacroPage

    app = _application()
    projection = build_macro_projection(
        generation_id=0,
        snapshots=(_snapshot(),),
        generated_at_utc=NOW,
    )
    unavailable = replace(
        projection,
        ai_status=Availability.UNAVAILABLE,
        ai_model_id="openai-responses:gpt-6-luna",
        ai_prompt_version="test-v1",
        ai_scope="GLOBAL-MARKET-CONTEXT",
        ai_summary="AI context unavailable; deterministic context only.",
        ai_directional_bias="unknown",
        ai_event_risk="unknown",
        ai_risk_flags=("AI_CONTEXT_UNAVAILABLE",),
        ai_generated_at_utc=NOW,
        ai_valid_until_utc=NOW + timedelta(minutes=10),
        ai_reason_codes=("AI_PROVIDER_RESPONSE_INCOMPLETE",),
    )
    language = LanguageManager("fr_FR")
    page = MacroPage(language)
    page.set_ai_key_present(True)
    page.set_snapshot(unavailable)
    app.processEvents()

    assert "Tentative IA terminée" in page._messages[3].text()
    assert "AI_PROVIDER_RESPONSE_INCOMPLETE" in page._messages[3].text()
    assert "Décision : WAIT" in page.ai_details.toPlainText()
    assert "Aucune analyse IA" not in page.ai_details.toPlainText()

    page.close()
    language.close()


def test_macro_page_keeps_worker_failure_visible_after_busy_state_ends() -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.macro_page import MacroPage

    app = _application()
    language = LanguageManager("fr_FR")
    page = MacroPage(language)
    page.set_ai_key_present(True)
    page.set_snapshot(
        build_macro_projection(
            generation_id=0,
            snapshots=(_snapshot(),),
            generated_at_utc=NOW,
        )
    )
    page.set_ai_busy(True)
    page.set_ai_error("macro.ai_failed")
    page.set_ai_busy(False)
    app.processEvents()

    assert "échoué" in page._messages[3].text()
    assert "réessayer" in page.ai_details.toPlainText()

    page.close()
    language.close()
