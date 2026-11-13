"""Incremental table model for configured scanner reference markets."""

from __future__ import annotations

from datetime import UTC, datetime

from PyQt5 import QtCore, QtGui

from trading_ig_assistant.app.projections.common import Availability
from trading_ig_assistant.app.projections.scanner import ScannerMarketRowVM
from trading_ig_assistant.app.projections.scanner_projection import scanner_last_price
from trading_ig_assistant.ui.i18n.language_manager import LanguageManager


class ScannerMarketTableModel(QtCore.QAbstractTableModel):
    _columns = (
        ("name", "scanner.column.market"),
        ("asset_class", "scanner.column.asset"),
        ("last", "scanner.column.last"),
        ("percent_change", "scanner.column.change"),
        ("freshness", "scanner.column.freshness"),
        ("technical_score", "scanner.column.technical"),
        ("context_score", "scanner.column.context"),
        ("signal_direction", "scanner.column.direction"),
        ("recommendation", "scanner.column.decision"),
        ("reason", "scanner.column.reason"),
        ("evaluated", "scanner.column.evaluated"),
    )

    def __init__(self, language: LanguageManager) -> None:
        super().__init__()
        self._language = language
        self._rows: tuple[ScannerMarketRowVM, ...] = ()

    @property
    def rows(self) -> tuple[ScannerMarketRowVM, ...]:
        return self._rows

    def set_rows(self, rows: tuple[ScannerMarketRowVM, ...]) -> None:
        identities = tuple(row.underlying_id for row in rows)
        if identities == tuple(row.underlying_id for row in self._rows):
            previous = self._rows
            self._rows = rows
            for row_index, (old, new) in enumerate(zip(previous, rows, strict=True)):
                if old != new:
                    self.dataChanged.emit(
                        self.index(row_index, 0),
                        self.index(row_index, len(self._columns) - 1),
                    )
            return
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent: QtCore.QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self._rows)

    def columnCount(self, parent: QtCore.QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self._columns)

    def headerData(self, section: int, orientation: int, role: int = 0) -> object:
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self._language.text(self._columns[section][1])
        return None

    def data(self, index: QtCore.QModelIndex, role: int = 0) -> object:
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        field = self._columns[index.column()][0]
        if role == QtCore.Qt.UserRole:
            return row.underlying_id
        if role == QtCore.Qt.UserRole + 1:
            return row.reference_epic
        if role == QtCore.Qt.ForegroundRole and field == "percent_change":
            if row.percent_change is not None:
                return QtGui.QColor("#22C55E" if row.percent_change >= 0 else "#EF4444")
        if role == QtCore.Qt.ForegroundRole and field == "context_score":
            return QtGui.QColor(
                {
                    "catalyst": "#22C55E",
                    "aligned": "#22C55E",
                    "caution": "#F59E0B",
                    "unfavorable": "#EF4444",
                }.get(row.context_level or "", "#94A3B8")
            )
        if role == QtCore.Qt.ToolTipRole:
            if field == "freshness":
                return " · ".join(
                    (
                        row.quote_provenance.source,
                        row.quote_provenance.availability.value,
                        *row.quote_provenance.reason_codes,
                    )
                )
            if field in {"reason", "recommendation"}:
                return ", ".join(row.reason_codes)
            if field == "context_score":
                return self._context_tooltip(row)
        if role != QtCore.Qt.DisplayRole:
            return None
        if field == "name":
            return row.name
        if field == "asset_class":
            return row.asset_class
        if field == "last":
            value = scanner_last_price(row)
            return "N/A" if value is None else str(value)
        if field == "percent_change":
            return "N/A" if row.percent_change is None else f"{row.percent_change}%"
        if field == "freshness":
            return _freshness(row, datetime.now(UTC))
        if field == "technical_score":
            return _score(row.technical_score)
        if field == "context_score":
            return self._context_display(row)
        if field == "signal_direction":
            return self._language.text(f"scanner.direction.{row.signal_direction}")
        if field == "recommendation":
            return self._language.text(f"scanner.decision.{row.recommendation}")
        if field == "reason":
            key = f"scanner.reason.{row.reason_codes[0].lower()}"
            message = self._language.text(key)
            if message == key:
                return ", ".join(row.reason_codes)
            return message.format(
                observed=row.observed_candles,
                required=row.required_candles,
            )
        if field == "evaluated":
            return (
                "N/A"
                if row.evaluated_at_utc is None
                else row.evaluated_at_utc.strftime("%H:%M:%S UTC")
            )
        return None

    def _context_display(self, row: ScannerMarketRowVM) -> str:
        if row.context_level is None:
            return self._language.text("scanner.context.unknown")
        label = self._language.text(f"scanner.context.{row.context_level}")
        return label if row.context_score is None else f"{label} · {row.context_score}/100"

    def _context_tooltip(self, row: ScannerMarketRowVM) -> str:
        if row.context_level is None:
            return self._language.text("scanner.context.no_evidence")
        return self._language.text("scanner.context.tooltip").format(
            components="\n".join(f"• {item}" for item in row.context_components) or "N/A",
            reasons=", ".join(row.context_reason_codes) or "N/A",
            provenance=", ".join(row.context_provenance) or "N/A",
            veto=self._language.text(
                "scanner.context.veto_yes"
                if row.context_safety_veto
                else "scanner.context.veto_no"
            ),
        )

    def retranslate_ui(self) -> None:
        self.headerDataChanged.emit(QtCore.Qt.Horizontal, 0, len(self._columns) - 1)
        if self._rows:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._rows) - 1, len(self._columns) - 1),
            )


def _score(value: object) -> str:
    return "INCONNU" if value is None else f"{value}/100"


def _freshness(row: ScannerMarketRowVM, now: datetime) -> str:
    provenance = row.quote_provenance
    if provenance.availability is not Availability.READY:
        return provenance.availability.value.upper()
    timestamp = provenance.observed_at_utc or provenance.received_at_utc
    if timestamp is None:
        return "READY"
    age = max(0, int((now - timestamp).total_seconds()))
    return f"{age}s · {provenance.source}"
