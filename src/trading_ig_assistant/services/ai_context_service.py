"""Validate provider-neutral AI context and build auditable snapshots."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

from trading_ig_assistant.domain.ai_context import (
    AIAnalysisStatus,
    MarketAIAnalysis,
    MarketAIProvider,
    MarketAIRequest,
    MarketContextSnapshot,
    is_ai_citation_eligible,
)
from trading_ig_assistant.domain.macro_context import (
    DirectionalBias,
    EventRisk,
    MacroRibbonState,
)

_OUTPUT_FIELDS = {
    "directional_bias",
    "event_risk",
    "confidence",
    "summary",
    "risk_flags",
    "source_signal_ids",
}


def build_market_context_snapshot(
    *,
    snapshot_id: str,
    instrument_id: str,
    macro_state: MacroRibbonState,
    generated_at_utc: datetime,
    valid_for: timedelta,
    prompt_version: str,
    provider: MarketAIProvider | None,
) -> MarketContextSnapshot:
    _require_utc(generated_at_utc)
    if valid_for <= timedelta(0):
        raise ValueError("market context validity duration must be positive")
    if not prompt_version.strip():
        raise ValueError("AI prompt version is required")

    reason_codes = list(macro_state.reason_codes)
    if provider is None:
        analysis = _fallback_analysis(
            model_id="unconfigured",
            prompt_version=prompt_version,
            instrument_id=instrument_id,
            generated_at_utc=generated_at_utc,
            valid_for=valid_for,
        )
        reason_codes.append("AI_PROVIDER_UNAVAILABLE")
    else:
        try:
            model_id = provider.model_id
        except Exception:  # provider boundary must degrade without leaking provider errors
            analysis = _fallback_analysis(
                model_id="invalid-provider",
                prompt_version=prompt_version,
                instrument_id=instrument_id,
                generated_at_utc=generated_at_utc,
                valid_for=valid_for,
            )
            reason_codes.append("AI_PROVIDER_ERROR")
        else:
            if not isinstance(model_id, str) or not model_id.strip():
                analysis = _fallback_analysis(
                    model_id="invalid-provider",
                    prompt_version=prompt_version,
                    instrument_id=instrument_id,
                    generated_at_utc=generated_at_utc,
                    valid_for=valid_for,
                )
                reason_codes.append("AI_PROVIDER_INVALID")
            else:
                request = MarketAIRequest(
                    instrument_id=instrument_id,
                    prompt_version=prompt_version,
                    macro_state=macro_state,
                    generated_at_utc=generated_at_utc,
                )
                try:
                    output = provider.analyze(request)
                except Exception:  # provider boundary must degrade without leaking provider errors
                    analysis = _fallback_analysis(
                        model_id=model_id,
                        prompt_version=prompt_version,
                        instrument_id=instrument_id,
                        generated_at_utc=generated_at_utc,
                        valid_for=valid_for,
                    )
                    reason_codes.append("AI_PROVIDER_ERROR")
                else:
                    try:
                        analysis = _parse_analysis(
                            output,
                            model_id=model_id,
                            prompt_version=prompt_version,
                            instrument_id=instrument_id,
                            macro_state=macro_state,
                            generated_at_utc=generated_at_utc,
                            valid_for=valid_for,
                        )
                    except (TypeError, ValueError, InvalidOperation):
                        analysis = _fallback_analysis(
                            model_id=model_id,
                            prompt_version=prompt_version,
                            instrument_id=instrument_id,
                            generated_at_utc=generated_at_utc,
                            valid_for=valid_for,
                        )
                        reason_codes.append("AI_OUTPUT_INVALID")

    provenance = tuple(
        dict.fromkeys(
            (
                *macro_state.provenance,
                f"ai_status:{analysis.status.value}",
                f"model:{analysis.model_id}",
                f"prompt:{analysis.prompt_version}",
                *(f"ai_source_signal:{item}" for item in analysis.source_signal_ids),
            )
        )
    )
    return MarketContextSnapshot(
        schema_version=1,
        snapshot_id=snapshot_id,
        instrument_id=instrument_id,
        macro_state=macro_state,
        ai_analysis=analysis,
        generated_at_utc=generated_at_utc,
        valid_until_utc=analysis.valid_until_utc,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        provenance=provenance,
    )


def _parse_analysis(
    output: Mapping[str, object],
    *,
    model_id: str,
    prompt_version: str,
    instrument_id: str,
    macro_state: MacroRibbonState,
    generated_at_utc: datetime,
    valid_for: timedelta,
) -> MarketAIAnalysis:
    if not isinstance(output, Mapping) or set(output) != _OUTPUT_FIELDS:
        raise ValueError("AI output fields do not match the typed contract")
    source_signal_ids = _string_sequence(output["source_signal_ids"], "source_signal_ids")
    active_signals = {
        signal.signal_id: signal
        for signal in macro_state.signals
        if is_ai_citation_eligible(signal, generated_at_utc)
    }
    if not source_signal_ids or any(item not in active_signals for item in source_signal_ids):
        raise ValueError("AI output references unavailable context signals")

    confidence = _decimal(output["confidence"], "confidence")
    requested_valid_until = generated_at_utc + valid_for
    source_expiries = [
        active_signals[item].valid_until_utc
        for item in source_signal_ids
        if active_signals[item].valid_until_utc is not None
    ]
    valid_until = min((requested_valid_until, *source_expiries))
    return MarketAIAnalysis(
        status=AIAnalysisStatus.AVAILABLE,
        model_id=model_id,
        prompt_version=prompt_version,
        market_scope=instrument_id,
        directional_bias=DirectionalBias(_text(output["directional_bias"], "directional_bias")),
        event_risk=EventRisk(_text(output["event_risk"], "event_risk")),
        confidence=confidence,
        summary=_text(output["summary"], "summary"),
        risk_flags=_string_sequence(output["risk_flags"], "risk_flags"),
        source_signal_ids=source_signal_ids,
        generated_at_utc=generated_at_utc,
        valid_until_utc=valid_until,
    )


def _fallback_analysis(
    *,
    model_id: str,
    prompt_version: str,
    instrument_id: str,
    generated_at_utc: datetime,
    valid_for: timedelta,
) -> MarketAIAnalysis:
    return MarketAIAnalysis(
        status=AIAnalysisStatus.UNAVAILABLE,
        model_id=model_id,
        prompt_version=prompt_version,
        market_scope=instrument_id,
        directional_bias=DirectionalBias.UNKNOWN,
        event_risk=EventRisk.UNKNOWN,
        confidence=None,
        summary="AI context unavailable; deterministic context only.",
        risk_flags=("AI_CONTEXT_UNAVAILABLE",),
        source_signal_ids=(),
        generated_at_utc=generated_at_utc,
        valid_until_utc=generated_at_utc + valid_for,
    )


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"AI output {field} must be non-empty text")
    return value.strip()


def _decimal(value: object, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, float, str)):
        raise TypeError(f"AI output {field} must be numeric")
    return Decimal(str(value))


def _string_sequence(value: object, field: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"AI output {field} must be a string array")
    items = tuple(_text(item, field) for item in value)
    if len(set(items)) != len(items):
        raise ValueError(f"AI output {field} values must be unique")
    return items


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("market context generation must use UTC")
