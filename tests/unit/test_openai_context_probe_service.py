from datetime import UTC, datetime

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.domain.ai_context import AIAnalysisStatus
from trading_ig_assistant.services import openai_context_probe_service as probe_service


def test_openai_probe_service_uses_only_synthetic_validation_context(monkeypatch) -> None:
    captured = {}

    class Provider:
        model_id = "openai-responses:test-model"

        def __init__(self, config):
            captured["config"] = config

        def analyze(self, request):
            captured["request"] = request
            signal = request.macro_state.signals[0]
            return {
                "directional_bias": "unknown",
                "event_risk": "medium",
                "confidence": 0.5,
                "summary": "Validation-only response",
                "risk_flags": ["VALIDATION_ONLY"],
                "source_signal_ids": [signal.signal_id],
            }

    monkeypatch.setattr(probe_service, "OpenAIResponsesMarketContextProvider", Provider)
    snapshot = probe_service.run_openai_context_probe(
        model="test-model",
        api_key=SecretValue("test-secret"),
        max_output_tokens=600,
        now=datetime(2026, 11, 4, 15, 0, tzinfo=UTC),
    )

    request = captured["request"]
    assert snapshot.instrument_id == "VALIDATION-ONLY"
    assert snapshot.ai_analysis.status is AIAnalysisStatus.AVAILABLE
    assert request.instrument_id == "VALIDATION-ONLY"
    assert len(request.macro_state.signals) == 1
    assert request.macro_state.signals[0].tags == ("validation_only", "central_bank")
    serialized = repr(request)
    assert "account" not in serialized.lower()
    assert "order" not in serialized.lower()
    assert "test-secret" not in repr(captured["config"])
