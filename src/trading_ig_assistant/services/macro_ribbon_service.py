"""Presentation-neutral macro ribbon projection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from trading_ig_assistant.domain.ai_context import AI_EVIDENCE_TAG
from trading_ig_assistant.domain.macro_context import ContextSeverity, MacroRibbonState


@dataclass(frozen=True)
class RibbonIndicator:
    key: str
    label: str
    value: str
    severity: ContextSeverity
    summary: str
    source: str | None = None
    observed_at_utc: datetime | None = None


class MacroRibbonService:
    """Project normalized state into stable ribbon cells; no Qt dependency."""

    def project(self, state: MacroRibbonState) -> tuple[RibbonIndicator, ...]:
        aggregate = (
            RibbonIndicator(
                "regime",
                "Global regime",
                state.regime.value,
                self._aggregate_severity(state.regime.value),
                "Normalized risk regime",
                "macro-context-engine",
                state.generated_at_utc,
            ),
            RibbonIndicator(
                "index_bias",
                "Index bias",
                state.index_bias.value,
                self._aggregate_severity(state.index_bias.value),
                "Normalized index direction",
                "macro-context-engine",
                state.generated_at_utc,
            ),
            RibbonIndicator(
                "gold_bias",
                "Gold context",
                state.gold_bias.value,
                self._aggregate_severity(state.gold_bias.value),
                "Normalized gold direction",
                "macro-context-engine",
                state.generated_at_utc,
            ),
            RibbonIndicator(
                "event_risk",
                "Event risk",
                state.event_risk.value,
                self._aggregate_severity(state.event_risk.value),
                "Normalized event severity",
                "macro-context-engine",
                state.generated_at_utc,
            ),
        )
        details = tuple(
            RibbonIndicator(
                f"signal:{signal.signal_id}",
                signal.label,
                signal.severity.value,
                signal.severity,
                signal.summary,
                signal.source,
                signal.observed_at_utc,
            )
            for signal in state.signals
            if AI_EVIDENCE_TAG not in {tag.lower() for tag in signal.tags}
        )
        return aggregate + details

    @staticmethod
    def _aggregate_severity(value: str) -> ContextSeverity:
        if value in {"unknown"}:
            return ContextSeverity.GRAY
        if value in {"risk_off", "bearish", "high"}:
            return ContextSeverity.RED
        if value in {"neutral", "medium"}:
            return ContextSeverity.YELLOW
        return ContextSeverity.GREEN
