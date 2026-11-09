"""Normalize provider-neutral context into a conservative macro state."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from trading_ig_assistant.domain.macro_context import (
    ContextSeverity,
    ContextSignal,
    DirectionalBias,
    EventRisk,
    MacroRibbonState,
    MarketRegime,
)


def _require_utc(timestamp: datetime) -> None:
    if timestamp.tzinfo is None or timestamp.utcoffset() != UTC.utcoffset(timestamp):
        raise ValueError("generated_at_utc must use UTC")


def _average(signals: tuple[ContextSignal, ...], tag: str) -> Decimal | None:
    values = [
        signal.score
        for signal in signals
        if tag in {item.lower() for item in signal.tags}
        and signal.severity is not ContextSeverity.GRAY
        and signal.score is not None
    ]
    if not values:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def _bias(value: Decimal | None) -> DirectionalBias:
    if value is None:
        return DirectionalBias.UNKNOWN
    if value >= Decimal("25"):
        return DirectionalBias.BULLISH
    if value <= Decimal("-25"):
        return DirectionalBias.BEARISH
    return DirectionalBias.NEUTRAL


class MacroContextService:
    """Build a ribbon state without inventing missing or stale context."""

    def revalidate_state(
        self,
        state: MacroRibbonState,
        evaluated_at_utc: datetime,
    ) -> MacroRibbonState:
        """Recompute expired signals when a stored aggregate is consumed later."""
        _require_utc(evaluated_at_utc)
        if state.generated_at_utc > evaluated_at_utc:
            empty = self.build_state((), evaluated_at_utc)
            return replace(empty, reason_codes=("CONTEXT_FROM_FUTURE", *empty.reason_codes))
        if any(
            signal.observed_at_utc > evaluated_at_utc
            or (signal.valid_until_utc is not None and signal.valid_until_utc <= evaluated_at_utc)
            for signal in state.signals
        ):
            return self.build_state(state.signals, evaluated_at_utc)
        return state

    def build_state(
        self,
        signals: tuple[ContextSignal, ...],
        generated_at_utc: datetime,
    ) -> MacroRibbonState:
        _require_utc(generated_at_utc)
        normalized: list[ContextSignal] = []
        reasons: list[str] = []
        for signal in signals:
            future = signal.observed_at_utc > generated_at_utc
            stale = (
                signal.valid_until_utc is not None and signal.valid_until_utc <= generated_at_utc
            )
            if future or stale:
                normalized.append(
                    replace(signal, severity=ContextSeverity.GRAY, score=None, confidence=None)
                )
                reasons.append(f"{'FUTURE' if future else 'STALE'}:{signal.signal_id}")
            else:
                normalized.append(signal)
        normalized_tuple = tuple(sorted(normalized, key=lambda signal: signal.signal_id))

        regime_score = _average(normalized_tuple, "risk")
        if regime_score is None:
            regime = MarketRegime.UNKNOWN
            reasons.append("REGIME_UNKNOWN")
        elif regime_score >= Decimal("25"):
            regime = MarketRegime.RISK_ON
        elif regime_score <= Decimal("-25"):
            regime = MarketRegime.RISK_OFF
        else:
            regime = MarketRegime.NEUTRAL

        index_bias = _bias(_average(normalized_tuple, "index"))
        gold_bias = _bias(_average(normalized_tuple, "gold"))
        if index_bias is DirectionalBias.UNKNOWN:
            reasons.append("INDEX_BIAS_UNKNOWN")
        if gold_bias is DirectionalBias.UNKNOWN:
            reasons.append("GOLD_BIAS_UNKNOWN")

        event_signals = [
            signal
            for signal in normalized_tuple
            if "event" in {tag.lower() for tag in signal.tags}
            and signal.severity is not ContextSeverity.GRAY
        ]
        severities = {signal.severity for signal in event_signals}
        if ContextSeverity.RED in severities:
            event_risk = EventRisk.HIGH
        elif ContextSeverity.YELLOW in severities:
            event_risk = EventRisk.MEDIUM
        elif event_signals and severities <= {ContextSeverity.GREEN}:
            event_risk = EventRisk.LOW
        else:
            event_risk = EventRisk.UNKNOWN
            reasons.append("EVENT_RISK_UNKNOWN")

        if not signals:
            reasons.insert(0, "NO_CONTEXT")
        provenance = tuple(
            dict.fromkeys(
                item
                for signal in normalized_tuple
                for item in (
                    f"signal:{signal.signal_id}",
                    f"source:{signal.source}",
                    *((f"url:{signal.source_url}",) if signal.source_url else ()),
                )
            )
        )
        return MacroRibbonState(
            schema_version=1,
            regime=regime,
            index_bias=index_bias,
            gold_bias=gold_bias,
            event_risk=event_risk,
            signals=normalized_tuple,
            generated_at_utc=generated_at_utc,
            reason_codes=tuple(dict.fromkeys(reasons)),
            provenance=provenance,
        )
