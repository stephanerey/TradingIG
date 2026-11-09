"""Accessible Qt projection of normalized macro context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from PyQt5 import QtWidgets

from trading_ig_assistant.domain.ai_context import AIAnalysisStatus, MarketAIAnalysis
from trading_ig_assistant.domain.macro_context import ContextSeverity, MacroRibbonState
from trading_ig_assistant.services.macro_ribbon_service import (
    MacroRibbonService,
    RibbonIndicator,
)


@dataclass(frozen=True)
class MacroStatusChip:
    label: str
    value: str = "unknown"
    status: ContextSeverity = ContextSeverity.GRAY
    summary: str = "Context unavailable"
    source: str | None = None
    observed_at: str | None = None


DEFAULT_MACRO_CHIPS = (
    MacroStatusChip("Global regime"),
    MacroStatusChip("Index bias"),
    MacroStatusChip("Gold context"),
    MacroStatusChip("Event risk"),
)

STATUS_COLORS = {
    ContextSeverity.GREEN: ("#0f7b45", "#e5f6ed"),
    ContextSeverity.YELLOW: ("#a26500", "#fff3cd"),
    ContextSeverity.RED: ("#a61b1b", "#fde7e7"),
    ContextSeverity.GRAY: ("#4f5965", "#eef1f4"),
}


class MacroRibbonWidget(QtWidgets.QWidget):
    def __init__(
        self,
        chips: tuple[MacroStatusChip, ...] | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setContentsMargins(8, 6, 8, 6)
        self._layout.setSpacing(6)
        self._labels: list[QtWidgets.QLabel] = []
        self._base_chips = chips or DEFAULT_MACRO_CHIPS
        self._ai_chip = MacroStatusChip(
            label="AI",
            value="inactive",
            status=ContextSeverity.GRAY,
            summary="OpenAI consultative context is not active for this session.",
        )
        self._render()

    def set_state(self, state: MacroRibbonState) -> None:
        """Replace ribbon contents from one normalized, versioned state."""
        indicators = MacroRibbonService().project(state)
        self._base_chips = tuple(self._chip_from_indicator(indicator) for indicator in indicators)
        self._render()

    def set_ai_analysis(
        self,
        analysis: MarketAIAnalysis,
        reason_codes: tuple[str, ...] = (),
        *,
        evaluated_at_utc: datetime | None = None,
        instrument_id: str | None = None,
        valid_until_utc: datetime | None = None,
    ) -> None:
        """Render consultative AI output separately from deterministic macro indicators."""

        evaluated_at = evaluated_at_utc or datetime.now(UTC)
        expires_at = min(analysis.valid_until_utc, valid_until_utc or analysis.valid_until_utc)
        if analysis.status is AIAnalysisStatus.AVAILABLE and (
            analysis.generated_at_utc > evaluated_at
            or expires_at <= evaluated_at
            or (
                instrument_id is not None
                and analysis.market_scope not in {"GLOBAL-MARKET-CONTEXT", instrument_id}
            )
        ):
            severity = ContextSeverity.GRAY
            if analysis.generated_at_utc > evaluated_at:
                value = "future"
                summary = "Analyse IA datée du futur ; contexte indisponible."
            elif expires_at <= evaluated_at:
                value = "stale"
                summary = "Analyse IA expirée ; contexte indisponible jusqu'au prochain résultat."
            else:
                value = "not-applicable"
                summary = "Analyse IA liée à un autre marché ; contexte indisponible ici."
            summary += f" Marché analysé : {analysis.market_scope}."
        elif analysis.status is AIAnalysisStatus.AVAILABLE:
            severity = {
                "high": ContextSeverity.RED,
                "medium": ContextSeverity.YELLOW,
                "low": ContextSeverity.GREEN,
            }.get(analysis.event_risk.value, ContextSeverity.GRAY)
            confidence = str(analysis.confidence) if analysis.confidence is not None else "unknown"
            summary = (
                "CONSULTATIF UNIQUEMENT — "
                f"{analysis.summary} Confidence déclarée: {confidence}; "
                f"sources: {', '.join(analysis.source_signal_ids)}; "
                f"marché: {analysis.market_scope}; "
                f"valide jusqu'à {expires_at.isoformat()}."
            )
            value = f"{analysis.directional_bias.value} / risk {analysis.event_risk.value}"
        else:
            severity = ContextSeverity.GRAY
            diagnostic = ", ".join(reason_codes) or "AI_UNAVAILABLE"
            summary = (
                "Contexte IA indisponible ; les indicateurs déterministes restent inchangés. "
                f"Diagnostic sûr: {diagnostic}."
            )
            value = "unavailable"
        self._ai_chip = MacroStatusChip(
            label="AI",
            value=value,
            status=severity,
            summary=summary,
            source=analysis.model_id,
            observed_at=analysis.generated_at_utc.isoformat(),
        )
        self._render()

    def _render(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        chips = (*self._base_chips, self._ai_chip)
        self._labels = [self._build_chip(chip) for chip in chips]
        for label in self._labels:
            self._layout.addWidget(label)
        self._layout.addStretch(1)

    @staticmethod
    def _chip_from_indicator(indicator: RibbonIndicator) -> MacroStatusChip:
        observed_at = (
            indicator.observed_at_utc.isoformat() if indicator.observed_at_utc is not None else None
        )
        return MacroStatusChip(
            label=indicator.label,
            value=indicator.value,
            status=indicator.severity,
            summary=indicator.summary,
            source=indicator.source,
            observed_at=observed_at,
        )

    def _build_chip(self, chip: MacroStatusChip) -> QtWidgets.QLabel:
        foreground, background = STATUS_COLORS[chip.status]
        label = QtWidgets.QLabel(f"{chip.label}: {chip.value} [{chip.status.value.upper()}]")
        details = [chip.summary]
        if chip.source:
            details.append(f"Source: {chip.source}")
        if chip.observed_at:
            details.append(f"Observed: {chip.observed_at}")
        label.setToolTip("\n".join(details))
        label.setAccessibleName(f"{chip.label}: {chip.value}, status {chip.status.value}")
        label.setStyleSheet(
            "QLabel {"
            f"color: {foreground};"
            f"background: {background};"
            "border-radius: 10px;"
            "padding: 4px 9px;"
            "font-weight: 600;"
            "}"
        )
        return label
