"""Auditable Paper analytics currently available to GUI V2."""

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.app.projections.dashboard import DashboardVM
from trading_ig_assistant.app.projections.optimization import OptimizationReviewVM
from trading_ig_assistant.app.projections.paper_history import PaperHistoryVM
from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
from trading_ig_assistant.ui.shell.page_specs import PAGE_SPEC_BY_KEY


class HistoryPage(QtWidgets.QWidget):
    def __init__(self, language: LanguageManager) -> None:
        super().__init__()
        self._language = language
        self._snapshot: DashboardVM | None = None
        self._paper_history: PaperHistoryVM | None = None
        self._optimization: OptimizationReviewVM | None = None
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        self.title = QtWidgets.QLabel()
        font = self.title.font()
        font.setPointSize(16)
        font.setBold(True)
        self.title.setFont(font)
        layout.addWidget(self.title)
        self.tabs = QtWidgets.QTabWidget()
        self._messages: list[QtWidgets.QLabel] = []
        journal_panel = QtWidgets.QWidget()
        journal_layout = QtWidgets.QVBoxLayout(journal_panel)
        self.journal_scope = QtWidgets.QLabel()
        self.journal_scope.setWordWrap(True)
        journal_layout.addWidget(self.journal_scope)
        self.journal_filter = QtWidgets.QLineEdit()
        self.journal_filter.textChanged.connect(self._apply_journal_filter)
        journal_layout.addWidget(self.journal_filter)
        self.journal_table = QtWidgets.QTableWidget(0, 6)
        self.journal_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.journal_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.journal_table.horizontalHeader().setStretchLastSection(True)
        journal_layout.addWidget(self.journal_table)
        self.tabs.addTab(journal_panel, "")
        pnl_panel = QtWidgets.QWidget()
        pnl_layout = QtWidgets.QVBoxLayout(pnl_panel)
        self.pnl_scope = QtWidgets.QLabel()
        self.pnl_scope.setWordWrap(True)
        pnl_layout.addWidget(self.pnl_scope)
        self.pnl_table = QtWidgets.QTableWidget(0, 4)
        self.pnl_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.pnl_table.horizontalHeader().setStretchLastSection(True)
        pnl_layout.addWidget(self.pnl_table)
        self.tabs.addTab(pnl_panel, "")
        statistics_panel = QtWidgets.QWidget()
        statistics_layout = QtWidgets.QVBoxLayout(statistics_panel)
        self.statistics_scope = QtWidgets.QLabel()
        self.statistics_scope.setWordWrap(True)
        statistics_layout.addWidget(self.statistics_scope)
        self.statistics_table = QtWidgets.QTableWidget(0, 2)
        self.statistics_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.statistics_table.horizontalHeader().setStretchLastSection(True)
        statistics_layout.addWidget(self.statistics_table)
        self.tabs.addTab(statistics_panel, "")
        optimization_panel = QtWidgets.QWidget()
        optimization_layout = QtWidgets.QVBoxLayout(optimization_panel)
        self.optimization_status = QtWidgets.QLabel()
        self.optimization_status.setWordWrap(True)
        optimization_layout.addWidget(self.optimization_status)
        self.optimization_scope = QtWidgets.QLabel()
        self.optimization_scope.setWordWrap(True)
        self.optimization_scope.setProperty("role", "muted")
        optimization_layout.addWidget(self.optimization_scope)
        self.optimization_table = QtWidgets.QTableWidget(0, 2)
        self.optimization_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.optimization_table.horizontalHeader().setStretchLastSection(True)
        optimization_layout.addWidget(self.optimization_table, stretch=1)
        self.tabs.addTab(optimization_panel, "")
        layout.addWidget(self.tabs, stretch=1)
        self.retranslate_ui()

    def _message_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        message = QtWidgets.QLabel()
        message.setAlignment(QtCore.Qt.AlignCenter)
        message.setWordWrap(True)
        layout.addWidget(message)
        self._messages.append(message)
        return panel

    def set_snapshot(self, snapshot: DashboardVM) -> None:
        self._snapshot = snapshot
        self._refresh()

    def set_paper_history(self, snapshot: PaperHistoryVM) -> None:
        self._paper_history = snapshot
        self._refresh_journal()

    def set_optimization(self, snapshot: OptimizationReviewVM) -> None:
        self._optimization = snapshot
        self._refresh_optimization()

    def retranslate_ui(self) -> None:
        self.title.setText(self._language.text("nav.history"))
        for index, key in enumerate(PAGE_SPEC_BY_KEY["history"].tab_keys):
            self.tabs.setTabText(index, self._language.text(key))
        self.pnl_table.setHorizontalHeaderLabels(
            tuple(
                self._language.text(key)
                for key in (
                    "history.period",
                    "history.period_key",
                    "history.amount",
                    "history.events",
                )
            )
        )
        self.journal_scope.setText(self._language.text("history.journal_scope"))
        self.journal_filter.setPlaceholderText(
            self._language.text("history.journal_filter")
        )
        self.journal_table.setHorizontalHeaderLabels(
            tuple(
                self._language.text(key)
                for key in (
                    "history.timestamp",
                    "history.event_type",
                    "history.instrument",
                    "history.correlation",
                    "history.pnl",
                    "history.pnl_status",
                )
            )
        )
        self.statistics_scope.setText(self._language.text("history.statistics_scope"))
        self.statistics_table.setHorizontalHeaderLabels(
            (
                self._language.text("history.metric"),
                self._language.text("history.value"),
            )
        )
        self.optimization_table.setHorizontalHeaderLabels(
            (
                self._language.text("optimization.evidence"),
                self._language.text("optimization.value"),
            )
        )
        self._refresh()
        self._refresh_journal()
        self._refresh_optimization()

    def _refresh(self) -> None:
        snapshot = self._snapshot
        totals = () if snapshot is None else snapshot.realized_pnl
        self.pnl_scope.setText(self._language.text("history.pnl_scope"))
        self.pnl_table.setRowCount(len(totals))
        for row_index, total in enumerate(totals):
            values = (
                total.period.value.upper(),
                total.period_key,
                f"{total.amount.value} {total.amount.currency}",
                str(total.event_count),
            )
            for column, value in enumerate(values):
                self.pnl_table.setItem(row_index, column, QtWidgets.QTableWidgetItem(value))
        self._refresh_statistics()

    def _refresh_statistics(self) -> None:
        snapshot = self._snapshot
        values: tuple[tuple[str, str], ...] = ()
        if snapshot is not None and snapshot.win_rate is not None:
            profit_factor = (
                str(snapshot.profit_factor)
                if snapshot.profit_factor is not None
                else "N/A"
            )
            drawdown = (
                f"{snapshot.drawdown.value} {snapshot.drawdown.currency}"
                if snapshot.drawdown is not None
                and snapshot.drawdown.value is not None
                else "N/A"
            )
            values = (
                (
                    self._language.text("history.win_rate"),
                    f"{snapshot.win_rate * 100:.2f}%",
                ),
                (self._language.text("history.profit_factor"), profit_factor),
                (self._language.text("history.drawdown"), drawdown),
            )
        self.statistics_table.setRowCount(len(values))
        for row, (metric, value) in enumerate(values):
            self.statistics_table.setItem(row, 0, QtWidgets.QTableWidgetItem(metric))
            self.statistics_table.setItem(row, 1, QtWidgets.QTableWidgetItem(value))

    def _refresh_journal(self) -> None:
        rows = () if self._paper_history is None else self._paper_history.rows
        self.journal_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            pnl = (
                f"{row.pnl_amount} {row.pnl_currency}"
                if row.pnl_amount is not None and row.pnl_currency is not None
                else "N/A"
            )
            values = (
                row.timestamp_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                _simulation_label(row.event_type),
                row.instrument_id or "N/A",
                row.correlation_id,
                pnl,
                row.pnl_status.value.upper(),
            )
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setData(QtCore.Qt.UserRole, row.event_id)
                self.journal_table.setItem(row_index, column, item)
        self._apply_journal_filter(self.journal_filter.text())

    def _refresh_optimization(self) -> None:
        snapshot = self._optimization
        if snapshot is None:
            self.optimization_status.setText(self._language.text("history.ai_unavailable"))
            self.optimization_scope.setText(self._language.text("optimization.safety"))
            self.optimization_table.setRowCount(0)
            return
        self.optimization_status.setText(
            self._language.text("optimization.status.insufficient").format(
                count=snapshot.trade_count
            )
        )
        self.optimization_scope.setText(
            self._language.text("optimization.scope_summary").format(
                scope=snapshot.scope,
                timestamp=snapshot.generated_at_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            )
        )
        rows = [
            (
                self._language.text("optimization.closed_trades"),
                str(snapshot.trade_count),
            ),
            (
                self._language.text("optimization.currencies"),
                ", ".join(snapshot.currencies) or "N/A",
            ),
            (
                self._language.text("optimization.dataset_version"),
                snapshot.dataset_version or "N/A",
            ),
            (
                self._language.text("optimization.external_ai"),
                self._language.text("optimization.not_authorized"),
            ),
            (
                self._language.text("optimization.proposals"),
                str(len(snapshot.proposals)),
            ),
        ]
        rows.extend(
            (
                self._language.text("optimization.blocker"),
                self._language.text(f"optimization.reason.{reason}"),
            )
            for reason in snapshot.reason_codes
        )
        self.optimization_table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for column, value in enumerate(values):
                self.optimization_table.setItem(
                    row,
                    column,
                    QtWidgets.QTableWidgetItem(value),
                )

    @QtCore.pyqtSlot(str)
    def _apply_journal_filter(self, text: str) -> None:
        query = text.strip().casefold()
        for row in range(self.journal_table.rowCount()):
            haystack = " ".join(
                self.journal_table.item(row, column).text()
                for column in range(self.journal_table.columnCount())
                if self.journal_table.item(row, column) is not None
            ).casefold()
            self.journal_table.setRowHidden(row, bool(query and query not in haystack))


def _simulation_label(value: str) -> str:
    return (
        value.replace("PAPER_", "SIMULATION_")
        .replace("PAPER-", "SIMULATION-")
        .replace("Paper", "simulation")
    )
