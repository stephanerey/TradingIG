from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.ai_context import AIAnalysisStatus, MarketAIRequest
from trading_ig_assistant.domain.macro_context import (
    ContextSeverity,
    ContextSignal,
    DirectionalBias,
    EventRisk,
)
from trading_ig_assistant.services.ai_context_service import build_market_context_snapshot
from trading_ig_assistant.services.macro_context_service import MacroContextService

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)


def _signal(*, stale: bool = False) -> ContextSignal:
    return ContextSignal(
        signal_id="SYNTHETIC-CONTEXT",
        label="Synthetic context",
        severity=ContextSeverity.GREEN,
        score=Decimal("50"),
        summary="Synthetic source for contract tests",
        source="synthetic-provider",
        source_url="https://example.invalid/context",
        observed_at_utc=NOW - timedelta(minutes=1),
        valid_until_utc=NOW - timedelta(seconds=1) if stale else NOW + timedelta(minutes=30),
        confidence=Decimal("0.8"),
        tags=("risk", "index"),
    )


def _macro_state(*, stale: bool = False):
    return MacroContextService().build_state((_signal(stale=stale),), NOW)


def _valid_output() -> dict[str, object]:
    return {
        "directional_bias": "bullish",
        "event_risk": "low",
        "confidence": "0.8",
        "summary": "Synthetic typed analysis",
        "risk_flags": [],
        "source_signal_ids": ["SYNTHETIC-CONTEXT"],
    }


class _SyntheticProvider:
    model_id = "synthetic-model-v1"

    def __init__(self, output: object | None = None, *, fail: bool = False) -> None:
        self.output = _valid_output() if output is None else output
        self.fail = fail
        self.requests: list[MarketAIRequest] = []

    def analyze(self, request: MarketAIRequest):
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("synthetic provider failure")
        return self.output


def _build(provider):
    return build_market_context_snapshot(
        snapshot_id="SYNTHETIC-SNAPSHOT",
        instrument_id="SYNTHETIC-INSTRUMENT",
        macro_state=_macro_state(),
        generated_at_utc=NOW,
        valid_for=timedelta(hours=1),
        prompt_version="prompt-v1",
        provider=provider,
    )


def test_valid_typed_analysis_preserves_model_prompt_sources_and_expiry() -> None:
    provider = _SyntheticProvider()

    snapshot = _build(provider)

    assert snapshot.ai_analysis.status is AIAnalysisStatus.AVAILABLE
    assert snapshot.ai_analysis.directional_bias is DirectionalBias.BULLISH
    assert snapshot.ai_analysis.event_risk is EventRisk.LOW
    assert snapshot.ai_analysis.confidence == Decimal("0.8")
    assert snapshot.valid_until_utc == NOW + timedelta(minutes=30)
    assert "model:synthetic-model-v1" in snapshot.provenance
    assert "prompt:prompt-v1" in snapshot.provenance
    assert "ai_source_signal:SYNTHETIC-CONTEXT" in snapshot.provenance
    assert provider.requests[0].macro_state == snapshot.macro_state


def test_missing_provider_is_explicitly_unavailable_and_unknown() -> None:
    snapshot = _build(None)

    assert snapshot.ai_analysis.status is AIAnalysisStatus.UNAVAILABLE
    assert snapshot.ai_analysis.directional_bias is DirectionalBias.UNKNOWN
    assert snapshot.ai_analysis.event_risk is EventRisk.UNKNOWN
    assert snapshot.ai_analysis.confidence is None
    assert snapshot.ai_analysis.source_signal_ids == ()
    assert "AI_PROVIDER_UNAVAILABLE" in snapshot.reason_codes


def test_provider_exception_degrades_without_leaking_or_fabricating_context() -> None:
    snapshot = _build(_SyntheticProvider(fail=True))

    assert snapshot.ai_analysis.status is AIAnalysisStatus.UNAVAILABLE
    assert snapshot.ai_analysis.risk_flags == ("AI_CONTEXT_UNAVAILABLE",)
    assert "AI_PROVIDER_ERROR" in snapshot.reason_codes

    class BrokenIdentityProvider:
        @property
        def model_id(self):
            raise RuntimeError("synthetic identity failure")

    identity_snapshot = _build(BrokenIdentityProvider())
    assert identity_snapshot.ai_analysis.status is AIAnalysisStatus.UNAVAILABLE
    assert "AI_PROVIDER_ERROR" in identity_snapshot.reason_codes


@pytest.mark.parametrize(
    "output",
    (
        {**_valid_output(), "unexpected": "field"},
        {**_valid_output(), "confidence": "1.5"},
        {**_valid_output(), "directional_bias": "up"},
        {**_valid_output(), "source_signal_ids": ["UNKNOWN-SOURCE"]},
        {key: value for key, value in _valid_output().items() if key != "summary"},
    ),
)
def test_malformed_or_untraceable_output_degrades_explicitly(output: object) -> None:
    snapshot = _build(_SyntheticProvider(output))

    assert snapshot.ai_analysis.status is AIAnalysisStatus.UNAVAILABLE
    assert "AI_OUTPUT_INVALID" in snapshot.reason_codes


def test_stale_context_cannot_be_cited_by_ai_output() -> None:
    snapshot = build_market_context_snapshot(
        snapshot_id="SYNTHETIC-SNAPSHOT",
        instrument_id="SYNTHETIC-INSTRUMENT",
        macro_state=_macro_state(stale=True),
        generated_at_utc=NOW,
        valid_for=timedelta(minutes=10),
        prompt_version="prompt-v1",
        provider=_SyntheticProvider(),
    )

    assert snapshot.ai_analysis.status is AIAnalysisStatus.UNAVAILABLE
    assert "AI_OUTPUT_INVALID" in snapshot.reason_codes


def test_request_requires_utc_positive_validity_and_prompt_version() -> None:
    arguments = {
        "snapshot_id": "SYNTHETIC-SNAPSHOT",
        "instrument_id": "SYNTHETIC-INSTRUMENT",
        "macro_state": _macro_state(),
        "generated_at_utc": NOW,
        "valid_for": timedelta(minutes=10),
        "prompt_version": "prompt-v1",
        "provider": None,
    }

    with pytest.raises(ValueError, match="UTC"):
        build_market_context_snapshot(**{**arguments, "generated_at_utc": NOW.replace(tzinfo=None)})
    with pytest.raises(ValueError, match="duration"):
        build_market_context_snapshot(**{**arguments, "valid_for": timedelta(0)})
    with pytest.raises(ValueError, match="prompt version"):
        build_market_context_snapshot(**{**arguments, "prompt_version": " "})
