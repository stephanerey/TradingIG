from datetime import UTC, datetime, timedelta

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.domain.ai_context import AIAnalysisStatus
from trading_ig_assistant.services.openai_web_research import WebResearchResult
from trading_ig_assistant.services.web_research_context import analyze_web_research


class Provider:
    model_id = "test-model"

    def analyze(self, request):
        signal = request.macro_state.signals[0]
        assert "secondaire" in signal.summary
        assert "https://example.org/article" in signal.summary
        return {
            "directional_bias": "bearish",
            "event_risk": "medium",
            "confidence": 0.6,
            "summary": "Pressions baissières, avec incertitude.",
            "risk_flags": ["UNCERTAIN"],
            "source_signal_ids": [signal.signal_id],
        }


def test_web_research_produces_scoped_expiring_sourced_snapshot():
    now = datetime(2026, 11, 6, tzinfo=UTC)
    result = WebResearchResult(
        "France 40", "test-model", "Résumé sourcé", (("https://example.org/article", "Titre"),)
    )
    snapshot = analyze_web_research(
        result, instrument_id="IX.CAC", api_key=SecretValue("unused"), now=now, provider=Provider()
    )
    assert snapshot.ai_analysis.status is AIAnalysisStatus.AVAILABLE
    assert snapshot.ai_analysis.directional_bias.value == "bearish"
    assert snapshot.instrument_id == "IX.CAC"
    assert snapshot.valid_until_utc == now + timedelta(minutes=10)
    assert snapshot.ai_analysis.source_signal_ids[0].startswith("web-research:")


def test_web_research_provider_failure_is_unavailable():
    class BadProvider:
        model_id = "test"

        def analyze(self, request):
            raise RuntimeError("sensitive details")

    result = WebResearchResult("France 40", "test", "Résumé", (("https://example.org", "S"),))
    snapshot = analyze_web_research(
        result, instrument_id="IX.CAC", api_key=SecretValue("unused"), provider=BadProvider()
    )
    assert snapshot.ai_analysis.status is AIAnalysisStatus.UNAVAILABLE
    assert "AI_PROVIDER_ERROR" in snapshot.reason_codes


def test_web_research_context_updates_only_matching_market_ribbon():
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    result = WebResearchResult(
        "France 40", "test-model", "Résumé sourcé", (("https://example.org/article", "Titre"),)
    )
    snapshot = analyze_web_research(
        result, instrument_id="IX.CAC", api_key=SecretValue("unused"), provider=Provider()
    )
    window = MainWindow()
    window._selected_product = TradableProduct(
        epic="IX.CAC", name="France 40", product_type=ProductType.CASH_OR_DFB
    )
    window._on_openai_context_success(snapshot)
    assert window.macro_ribbon._ai_chip.value == "bearish / risk medium"
    window._selected_product = TradableProduct(
        epic="IX.OTHER", name="Autre", product_type=ProductType.CASH_OR_DFB
    )
    window._refresh_ai_presentation()
    assert window.macro_ribbon._ai_chip.value == "not-applicable"
    window.close()
    assert app is not None


def test_product_list_uses_explicit_reference_binding_without_changing_scanner_scope():
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_navigation import IGProductMarketBinding
    from trading_ig_assistant.domain.markets import CanonicalUnderlyingId
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.services.product_discovery_service import ProductDiscoveryResult
    from trading_ig_assistant.ui.product_selector import (
        PRODUCT_CONTEXT_COLUMN,
        ProductSelectorWidget,
    )

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    result = WebResearchResult(
        "France 40", "test-model", "Résumé sourcé", (("https://example.org/article", "Titre"),)
    )
    snapshot = analyze_web_research(
        result, instrument_id="REF", api_key=SecretValue("unused"), provider=Provider()
    )
    product = TradableProduct(
        epic="BARRIER", name="France 40 Barrières Vente", product_type=ProductType.BARRIER
    )
    widget = ProductSelectorWidget()
    widget.set_results([ProductDiscoveryResult("fixture", 1, [product])])
    widget.set_market_context(snapshot.macro_state, snapshot)
    assert "not-applicable" in widget.product_table.item(0, PRODUCT_CONTEXT_COLUMN).text()
    widget.set_market_bindings(
        (
            IGProductMarketBinding(
                product_epic="BARRIER",
                canonical_underlying_id=CanonicalUnderlyingId.FRANCE_40,
                reference_epic="REF",
                provenance=("fixture:verified",),
            ),
        )
    )
    item = widget.product_table.item(0, PRODUCT_CONTEXT_COLUMN)
    assert "ai:bearish (référence)" in item.text()
    assert "fixture:verified" in item.toolTip()
    assert app is not None
