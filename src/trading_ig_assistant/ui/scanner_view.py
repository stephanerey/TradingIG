"""Analysis-only Qt view for deterministic strategy signals."""

from __future__ import annotations

from decimal import Decimal

from PyQt5 import QtCore, QtGui, QtWidgets

from trading_ig_assistant.domain.analysis import (
    ScannerResult,
    ScoreBand,
    ScoreComponentName,
    StrategySignal,
)
from trading_ig_assistant.services.product_context_projection_service import (
    ProductContextLevel,
    ProductContextProjection,
)
from trading_ig_assistant.services.scanner_preview_service import ScannerPreview
from trading_ig_assistant.ui.score_palette import SCORE_BAND_COLORS

CONTEXT_COLORS = {
    level: SCORE_BAND_COLORS[band]
    for level, band in {
        ProductContextLevel.CATALYST: ScoreBand.EXCEPTIONAL,
        ProductContextLevel.ALIGNED: ScoreBand.FAVORABLE,
        ProductContextLevel.CAUTION: ScoreBand.CAUTION,
        ProductContextLevel.UNFAVORABLE: ScoreBand.UNFAVORABLE,
        ProductContextLevel.UNKNOWN: ScoreBand.UNKNOWN,
    }.items()
}


class ScannerPreviewWidget(QtWidgets.QWidget):
    refresh_requested = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        self.safety = QtWidgets.QLabel(
            "ANALYSE UNIQUEMENT — paramètres preview non validés pour AUTO ; aucun ticket ni ordre."
        )
        self.safety.setWordWrap(True)
        self.safety.setStyleSheet(
            "QLabel { background: #fff3cd; color: #7a5200; padding: 6px; font-weight: 600; }"
        )
        layout.addWidget(self.safety)
        controls = QtWidgets.QHBoxLayout()
        self.refresh_button = QtWidgets.QPushButton("Analyser les bougies clôturées")
        self.refresh_button.clicked.connect(self.refresh_requested)
        controls.addWidget(self.refresh_button)
        controls.addStretch(1)
        layout.addLayout(controls)
        self.status = QtWidgets.QLabel("Aucune analyse lancée.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.table = QtWidgets.QTableWidget(0, 16)
        self.table.setHorizontalHeaderLabels(
            (
                "Stratégie",
                "Signal",
                "Contexte",
                "Technique",
                "R/R",
                "Risque",
                "Coûts",
                "Qualité",
                "Score",
                "Décision",
                "État",
                "Raisons",
                "Entrée",
                "Stop",
                "Objectif",
                "Valide jusqu'à",
            )
        )
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumSize(0, 0)
        layout.addWidget(self.table, stretch=1)

    def show_unavailable(self, message: str) -> None:
        self.status.setText(message)
        self.table.setRowCount(0)

    def set_preview(
        self,
        preview: ScannerPreview,
        context: ProductContextProjection | None = None,
        score_results: tuple[ScannerResult, ...] = (),
    ) -> None:
        gap_message = (
            f" · DATA_GAP : {preview.excluded_pre_gap_candles} ancienne(s) bougie(s) exclue(s)"
            if preview.excluded_pre_gap_candles
            else ""
        )
        context_status = (
            f" · contexte {context.label} ({', '.join(context.components)})"
            if context is not None
            else " · contexte INCONNU"
        )
        self.status.setText(
            f"{preview.instrument_id} · {preview.timeframe} · "
            f"{preview.used_closed_candles} bougies utilisées · "
            f"consensus {preview.consensus.status.value}{gap_message}{context_status}. "
            "EVENT_DRIVEN inactif sans contexte qualifié."
        )
        self.table.setRowCount(len(preview.signals))
        results_by_signal = {result.signal_id: result for result in score_results}
        for row, signal in enumerate(preview.signals):
            result = results_by_signal.get(signal.signal_id)
            values = (
                signal.strategy_id,
                signal.side.value.upper(),
                context.compact_text if context is not None else "INCONNU",
                _format_component(result, ScoreComponentName.TECHNICAL),
                _format_component(result, ScoreComponentName.REWARD_RISK),
                _format_component(result, ScoreComponentName.MARKET_RISK),
                _format_component(result, ScoreComponentName.EXECUTION_COST),
                _format_component(result, ScoreComponentName.DATA_QUALITY),
                _format_score(result),
                result.recommendation.value if result is not None else "no_trade",
                signal.data_state.value,
                ", ".join(signal.reason_codes),
                _format_entry(signal),
                _format_decimal(signal.invalidation),
                _format_decimal(signal.target),
                signal.valid_until_utc.isoformat(),
            )
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if column == 2 and context is not None:
                    item.setToolTip(context.tooltip)
                    foreground, background = CONTEXT_COLORS[context.level]
                    item.setForeground(QtGui.QBrush(QtGui.QColor(foreground)))
                    item.setBackground(QtGui.QBrush(QtGui.QColor(background)))
                elif 3 <= column <= 7 and result is not None:
                    component_names = (
                        ScoreComponentName.TECHNICAL,
                        ScoreComponentName.REWARD_RISK,
                        ScoreComponentName.MARKET_RISK,
                        ScoreComponentName.EXECUTION_COST,
                        ScoreComponentName.DATA_QUALITY,
                    )
                    component = next(
                        item
                        for item in result.components
                        if item.name is component_names[column - 3]
                    )
                    band = component.band or ScoreBand.UNKNOWN
                    if component.name is ScoreComponentName.DATA_QUALITY:
                        item.setToolTip(
                            "Score fondé sur les contrôles disponibles de fraîcheur, continuité "
                            "et disponibilité ; il ne vérifie pas indépendamment l'exactitude "
                            "des prix ni l'absence de valeurs aberrantes."
                        )
                    foreground, background = SCORE_BAND_COLORS[band]
                    item.setForeground(QtGui.QBrush(QtGui.QColor(foreground)))
                    item.setBackground(QtGui.QBrush(QtGui.QColor(background)))
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()


def _format_entry(signal: StrategySignal) -> str:
    if signal.entry_zone is None:
        return "-"
    return f"{signal.entry_zone[0]} … {signal.entry_zone[1]}"


def _format_decimal(value: Decimal | None) -> str:
    return "-" if value is None else str(value)


def _format_component(
    result: ScannerResult | None,
    name: ScoreComponentName,
) -> str:
    if result is None:
        return "INCONNU"
    component = next(item for item in result.components if item.name is name)
    if component.score is None:
        return "INCONNU"
    band = component.band.value if component.band is not None else "unclassified"
    return f"{component.score}/100 {band}"


def _format_score(result: ScannerResult | None) -> str:
    if result is None or result.ranking_score is None:
        return "INDISPONIBLE"
    return f"{result.ranking_score}/100"
