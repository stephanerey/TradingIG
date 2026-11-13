"""Read-only Qt model for IG catalogue search rows."""

from __future__ import annotations

from PyQt5 import QtCore, QtGui

from trading_ig_assistant.app.projections.catalogue import ProductRowVM
from trading_ig_assistant.app.projections.common import Availability
from trading_ig_assistant.ui.i18n.language_manager import LanguageManager


class ProductTableModel(QtCore.QAbstractTableModel):
    _columns = (
        ("freshness", "catalogue.column.live"),
        ("name", "catalogue.column.name"),
        ("epic", "catalogue.column.epic"),
        ("product_type", "catalogue.column.type"),
        ("direction", "catalogue.column.direction"),
        ("asset_class", "catalogue.column.asset"),
        ("bid", "catalogue.column.bid"),
        ("offer", "catalogue.column.offer"),
        ("percent_change", "catalogue.column.change"),
        ("provenance", "catalogue.column.source"),
        ("status", "catalogue.column.status"),
    )

    def __init__(self, language: LanguageManager) -> None:
        super().__init__()
        self._language = language
        self._rows: tuple[ProductRowVM, ...] = ()

    def set_rows(self, rows: tuple[ProductRowVM, ...]) -> None:
        if tuple(row.epic for row in self._rows) == tuple(row.epic for row in rows):
            previous = self._rows
            self._rows = rows
            for row_index, (old_row, new_row) in enumerate(zip(previous, rows, strict=True)):
                if old_row == new_row:
                    continue
                self.dataChanged.emit(
                    self.index(row_index, 0),
                    self.index(row_index, len(self._columns) - 1),
                    [
                        QtCore.Qt.DisplayRole,
                        QtCore.Qt.DecorationRole,
                        QtCore.Qt.ToolTipRole,
                        QtCore.Qt.UserRole,
                    ],
                )
            return
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def epic_at(self, row: int) -> str | None:
        if not 0 <= row < len(self._rows):
            return None
        return self._rows[row].epic

    def row_at(self, row: int) -> ProductRowVM | None:
        if not 0 <= row < len(self._rows):
            return None
        return self._rows[row]

    def row_for_epic(self, epic: str) -> int | None:
        return next((index for index, row in enumerate(self._rows) if row.epic == epic), None)

    def rowCount(self, parent: QtCore.QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self._rows)

    def columnCount(self, parent: QtCore.QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self._columns)

    def headerData(self, section: int, orientation: int, role: int = 0) -> object:
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self._language.text(self._columns[section][1])
        if (
            role == QtCore.Qt.ToolTipRole
            and orientation == QtCore.Qt.Horizontal
            and self._columns[section][0] == "freshness"
        ):
            return self._language.text("catalogue.live.header_tooltip")
        return None

    def data(self, index: QtCore.QModelIndex, role: int = 0) -> object:
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        field = self._columns[index.column()][0]
        if role == QtCore.Qt.UserRole:
            return row.epic
        if field == "freshness":
            is_live = (
                row.provenance.source == "ig-lightstreamer"
                and row.provenance.availability == Availability.READY
            )
            if role == QtCore.Qt.DecorationRole:
                return QtGui.QColor("#22C55E" if is_live else "#64748B")
            if role == QtCore.Qt.ToolTipRole:
                key = "catalogue.live.updated" if is_live else "catalogue.live.not_updated"
                return self._language.text(key)
            if role == QtCore.Qt.TextAlignmentRole:
                return QtCore.Qt.AlignCenter
            return None
        if role == QtCore.Qt.ToolTipRole and field == "provenance":
            observed = row.provenance.observed_at_utc
            timestamp = observed.isoformat() if observed is not None else "N/A"
            return f"{row.provenance.source} · {row.provenance.availability.value} · {timestamp}"
        if role != QtCore.Qt.DisplayRole:
            return None
        value = getattr(row, field)
        if field == "provenance":
            if value.source == "ig-lightstreamer":
                return "LIVE" if value.availability.value == "ready" else "STALE"
            if value.source == "local-discovery-cache":
                return "CACHE"
            return "REST"
        if value is None:
            return "N/A"
        if field == "percent_change":
            return f"{value}%"
        return str(value)

    def retranslate_ui(self) -> None:
        self.headerDataChanged.emit(QtCore.Qt.Horizontal, 0, len(self._columns) - 1)
