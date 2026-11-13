"""Read-only table model for Paper position projections."""

from __future__ import annotations

from decimal import Decimal

from PyQt5 import QtCore

from trading_ig_assistant.app.projections.common import Amount, Availability
from trading_ig_assistant.app.projections.dashboard import PositionRowVM
from trading_ig_assistant.ui.i18n.language_manager import LanguageManager


class PositionTableModel(QtCore.QAbstractTableModel):
    _columns = (
        ("product_id", "dashboard.position.product"),
        ("direction", "dashboard.position.direction"),
        ("quantity", "dashboard.position.quantity"),
        ("entry_price", "dashboard.position.entry"),
        ("mark_price", "dashboard.position.mark"),
        ("net_pnl", "dashboard.position.pnl"),
        ("current_stop", "dashboard.position.stop"),
        ("status", "dashboard.position.status"),
    )

    def __init__(self, language: LanguageManager) -> None:
        super().__init__()
        self._language = language
        self._rows: tuple[PositionRowVM, ...] = ()

    @property
    def rows(self) -> tuple[PositionRowVM, ...]:
        return self._rows

    def set_rows(self, rows: tuple[PositionRowVM, ...]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def retranslate_ui(self) -> None:
        if self.columnCount() > 0:
            self.headerDataChanged.emit(QtCore.Qt.Horizontal, 0, self.columnCount() - 1)

    def rowCount(self, parent: QtCore.QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self._rows)

    def columnCount(self, parent: QtCore.QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self._columns)

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.DisplayRole,
    ) -> object:
        if (
            role == QtCore.Qt.DisplayRole
            and orientation == QtCore.Qt.Horizontal
            and 0 <= section < len(self._columns)
        ):
            return self._language.text(self._columns[section][1])
        return None

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        row = self._rows[index.row()]
        field = self._columns[index.column()][0]
        value = getattr(row, field)
        if role == QtCore.Qt.UserRole:
            return row.position_id
        if role == QtCore.Qt.TextAlignmentRole and field in {
            "quantity",
            "entry_price",
            "mark_price",
            "net_pnl",
            "current_stop",
        }:
            return int(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        if role == QtCore.Qt.ToolTipRole and isinstance(value, Amount):
            reasons = ", ".join(value.provenance.reason_codes)
            return f"{value.provenance.availability.value} · {reasons or value.provenance.source}"
        if role != QtCore.Qt.DisplayRole:
            return None
        if isinstance(value, Amount):
            return _amount(value)
        if isinstance(value, Decimal):
            return _decimal(value)
        return str(value).upper() if field in {"direction", "status"} else str(value)


def _amount(amount: Amount) -> str:
    if amount.value is None:
        if amount.provenance.availability is Availability.STALE:
            return "N/A · stale"
        return "N/A"
    marker = "~" if amount.estimate else ""
    return f"{marker}{_decimal(amount.value)} {amount.currency.upper()}"


def _decimal(value: Decimal) -> str:
    rendered = format(value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered
