"""Honest read-only dashboard for the current local Paper session."""

from __future__ import annotations

from datetime import datetime

import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.app.projections.common import Amount
from trading_ig_assistant.app.projections.dashboard import DashboardVM
from trading_ig_assistant.app.projections.optimization import OptimizationReviewVM
from trading_ig_assistant.domain.journal import PnlPeriod
from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
from trading_ig_assistant.ui.models.position_table_model import PositionTableModel


class DashboardPage(QtWidgets.QWidget):
    def __init__(self, language: LanguageManager) -> None:
        super().__init__()
        self._language = language
        self._snapshot: DashboardVM | None = None
        self._optimization: OptimizationReviewVM | None = None
        self._kpis: dict[str, _KpiCard] = {}

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        self.title_label = QtWidgets.QLabel()
        title_font = self.title_label.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)
        self.scope_label = QtWidgets.QLabel()
        self.scope_label.setProperty("role", "muted")
        self.scope_label.setWordWrap(True)
        self.scope_label.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Preferred,
        )
        layout.addWidget(self.scope_label)

        self.tabs = QtWidgets.QTabWidget()
        self.overview = QtWidgets.QWidget()
        overview_layout = QtWidgets.QVBoxLayout(self.overview)
        kpi_grid = QtWidgets.QGridLayout()
        for index, key in enumerate(
            (
                "equity",
                "balance",
                "available",
                "account_pnl",
                "margin",
                "day_pnl",
                "week_pnl",
                "month_pnl",
                "positions",
                "win_rate",
                "profit_factor",
                "drawdown",
            )
        ):
            card = _KpiCard()
            self._kpis[key] = card
            kpi_grid.addWidget(card, index // 4, index % 4)
        overview_layout.addLayout(kpi_grid)
        self.positions_title = QtWidgets.QLabel()
        overview_layout.addWidget(self.positions_title)
        self.position_model = PositionTableModel(language)
        self.positions_table = QtWidgets.QTableView()
        self.positions_table.setModel(self.position_model)
        self.positions_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.positions_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.positions_table.horizontalHeader().setStretchLastSection(True)
        overview_layout.addWidget(self.positions_table, stretch=1)
        self.positions_empty = QtWidgets.QLabel()
        self.positions_empty.setAlignment(QtCore.Qt.AlignCenter)
        self.positions_empty.setProperty("role", "muted")
        overview_layout.addWidget(self.positions_empty)

        self.performance = QtWidgets.QWidget()
        performance_layout = QtWidgets.QVBoxLayout(self.performance)
        self.performance_message = QtWidgets.QLabel()
        self.performance_message.setWordWrap(True)
        self.performance_message.setAlignment(QtCore.Qt.AlignTop)
        performance_layout.addWidget(self.performance_message)
        performance_controls = QtWidgets.QHBoxLayout()
        self.performance_period = QtWidgets.QComboBox()
        for period in PnlPeriod:
            self.performance_period.addItem("", period.value)
        self.performance_currency = QtWidgets.QComboBox()
        self.performance_mode = QtWidgets.QComboBox()
        self.performance_mode.addItem("", "currency")
        self.performance_mode.addItem("", "percent")
        performance_controls.addWidget(self.performance_period)
        performance_controls.addWidget(self.performance_currency)
        performance_controls.addWidget(self.performance_mode)
        performance_controls.addStretch(1)
        performance_layout.addLayout(performance_controls)
        self.performance_plot = pg.PlotWidget()
        self.performance_plot.setBackground("#0C1627")
        self.performance_plot.showGrid(x=True, y=True, alpha=0.25)
        self.performance_plot.setLabel("left", "PnL")
        self.performance_plot.setMinimumHeight(260)
        self.performance_plot.setMouseEnabled(x=False, y=False)
        self.performance_plot.hideButtons()
        self.performance_plot.setMenuEnabled(False)
        for axis_name in ("left", "bottom"):
            axis = self.performance_plot.getAxis(axis_name)
            axis.setPen(pg.mkPen("#526784"))
            axis.setTextPen(pg.mkPen("#D7E5F8"))
        performance_layout.addWidget(self.performance_plot, stretch=1)
        self.equity_history_message = QtWidgets.QLabel()
        self.equity_history_message.setWordWrap(True)
        self.equity_history_message.setProperty("role", "muted")
        performance_layout.addWidget(self.equity_history_message)
        self.performance_period.currentIndexChanged.connect(self._refresh_performance)
        self.performance_currency.currentIndexChanged.connect(self._refresh_performance)
        self.performance_mode.currentIndexChanged.connect(self._refresh_performance)

        self.ai_improvement = QtWidgets.QWidget()
        ai_layout = QtWidgets.QVBoxLayout(self.ai_improvement)
        self.ai_message = QtWidgets.QLabel()
        self.ai_message.setWordWrap(True)
        self.ai_message.setAlignment(QtCore.Qt.AlignCenter)
        ai_layout.addWidget(self.ai_message)
        self.ai_evidence = QtWidgets.QTableWidget(0, 2)
        self.ai_evidence.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.ai_evidence.horizontalHeader().setStretchLastSection(True)
        ai_layout.addWidget(self.ai_evidence, stretch=1)

        self.tabs.addTab(self.overview, "")
        self.tabs.addTab(self.performance, "")
        self.tabs.addTab(self.ai_improvement, "")
        layout.addWidget(self.tabs, stretch=1)
        self.retranslate_ui()

    def set_snapshot(self, snapshot: DashboardVM) -> None:
        self._snapshot = snapshot
        self.position_model.set_rows(snapshot.open_positions)
        self._refresh_values()

    def set_optimization(self, snapshot: OptimizationReviewVM) -> None:
        self._optimization = snapshot
        self._refresh_optimization()

    def retranslate_ui(self) -> None:
        self.title_label.setText(self._language.text("nav.dashboard"))
        self.tabs.setTabText(0, self._language.text("tab.overview"))
        self.tabs.setTabText(1, self._language.text("tab.performance"))
        self.tabs.setTabText(2, self._language.text("tab.ai_improvement"))
        self.ai_evidence.setHorizontalHeaderLabels(
            (
                self._language.text("optimization.evidence"),
                self._language.text("optimization.value"),
            )
        )
        self.positions_title.setText(self._language.text("dashboard.positions.title"))
        labels = {
            "equity": "dashboard.kpi.equity",
            "balance": "dashboard.kpi.balance",
            "available": "dashboard.kpi.available",
            "account_pnl": "dashboard.kpi.account_pnl",
            "margin": "dashboard.kpi.margin",
            "day_pnl": "dashboard.kpi.day_pnl",
            "week_pnl": "dashboard.kpi.week_pnl",
            "month_pnl": "dashboard.kpi.month_pnl",
            "positions": "dashboard.kpi.positions",
            "win_rate": "dashboard.kpi.win_rate",
            "profit_factor": "dashboard.kpi.profit_factor",
            "drawdown": "dashboard.kpi.drawdown",
        }
        for key, message_id in labels.items():
            self._kpis[key].set_title(self._language.text(message_id))
        self.position_model.retranslate_ui()
        for index, period in enumerate(PnlPeriod):
            self.performance_period.setItemText(
                index,
                self._language.text(f"dashboard.performance.period.{period.value}"),
            )
        self.performance_mode.setItemText(
            0,
            self._language.text("dashboard.performance.mode.currency"),
        )
        self.performance_mode.setItemText(
            1,
            self._language.text("dashboard.performance.mode.percent"),
        )
        self._refresh_values()
        self._refresh_optimization()

    def _refresh_values(self) -> None:
        snapshot = self._snapshot
        if snapshot is None:
            self.scope_label.setText(self._language.text("dashboard.scope.unavailable"))
            for card in self._kpis.values():
                card.set_value("N/A")
            self.position_model.set_rows(())
            self.positions_empty.setText(self._language.text("dashboard.positions.empty"))
            self.positions_empty.setVisible(True)
            self.performance_message.setText(
                self._language.text("dashboard.performance.unavailable")
            )
            self.equity_history_message.setText(
                self._language.text("dashboard.performance.no_equity_history")
            )
            self._clear_performance_plot()
            self._refresh_optimization()
            return
        self.scope_label.setText(
            self._language.text("dashboard.scope.paper").format(
                account=snapshot.account_id,
                timestamp=_utc_text(snapshot.generated_at_utc),
            )
        )
        self._kpis["balance"].set_value(_amount(snapshot.account_balance))
        self._kpis["equity"].set_value(_amount(snapshot.equity))
        self._kpis["available"].set_value(_amount(snapshot.available_funds))
        self._kpis["account_pnl"].set_value(_amount(snapshot.account_profit_loss))
        self._kpis["margin"].set_value(_amount(snapshot.margin_deposit))
        self._kpis["day_pnl"].set_value(_period_pnl(snapshot, PnlPeriod.DAY))
        self._kpis["week_pnl"].set_value(_period_pnl(snapshot, PnlPeriod.WEEK))
        self._kpis["month_pnl"].set_value(_period_pnl(snapshot, PnlPeriod.MONTH))
        self._kpis["positions"].set_value(str(len(snapshot.open_positions)))
        self._kpis["win_rate"].set_value(
            f"{snapshot.win_rate * 100:.2f}%" if snapshot.win_rate is not None else "N/A"
        )
        self._kpis["profit_factor"].set_value(
            format(snapshot.profit_factor, "f")
            if snapshot.profit_factor is not None
            else "N/A"
        )
        self._kpis["drawdown"].set_value(_amount(snapshot.drawdown))
        self.positions_empty.setText(self._language.text("dashboard.positions.empty"))
        self.positions_empty.setVisible(not snapshot.open_positions)
        self._sync_performance_currencies()
        self._refresh_performance()
        self.equity_history_message.setText(
            self._language.text("dashboard.performance.no_equity_history")
        )
        self._refresh_optimization()

    def _refresh_optimization(self) -> None:
        snapshot = self._optimization
        if snapshot is None:
            self.ai_message.setText(self._language.text("dashboard.ai.unavailable"))
            self.ai_evidence.setRowCount(0)
            return
        self.ai_message.setText(
            self._language.text("optimization.status.insufficient").format(
                count=snapshot.trade_count
            )
        )
        rows = (
            (
                self._language.text("optimization.scope"),
                snapshot.scope,
            ),
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
        )
        self.ai_evidence.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for column, value in enumerate(values):
                self.ai_evidence.setItem(row, column, QtWidgets.QTableWidgetItem(value))

    def _sync_performance_currencies(self) -> None:
        snapshot = self._snapshot
        currencies = (
            ()
            if snapshot is None
            else tuple(sorted({item.amount.currency.upper() for item in snapshot.realized_pnl}))
        )
        selected = self.performance_currency.currentData()
        self.performance_currency.blockSignals(True)
        self.performance_currency.clear()
        for currency in currencies:
            self.performance_currency.addItem(currency, currency)
        index = self.performance_currency.findData(selected)
        self.performance_currency.setCurrentIndex(index if index >= 0 else 0)
        self.performance_currency.blockSignals(False)

    @QtCore.pyqtSlot()
    def _refresh_performance(self, *_args: object) -> None:
        snapshot = self._snapshot
        if snapshot is None:
            self._clear_performance_plot()
            return
        if self.performance_mode.currentData() == "percent":
            self._clear_performance_plot()
            self.performance_message.setText(
                self._language.text("dashboard.performance.percent_unavailable")
            )
            return
        period_value = self.performance_period.currentData() or PnlPeriod.DAY.value
        currency = self.performance_currency.currentData()
        rows = tuple(
            item
            for item in snapshot.realized_pnl
            if item.period.value == period_value
            and item.amount.currency.upper() == currency
            and item.amount.value is not None
        )
        self._clear_performance_plot()
        if not rows:
            self.performance_message.setText(
                self._language.text("dashboard.performance.no_realized_pnl")
            )
            return
        ordered = tuple(sorted(rows, key=lambda item: item.period_key))
        ticks: list[tuple[float, str]] = []
        for index, item in enumerate(ordered):
            value = float(item.amount.value or 0)
            self.performance_plot.addItem(
                pg.BarGraphItem(
                    x=[index],
                    height=[value],
                    width=0.72,
                    brush=pg.mkBrush("#22C55E" if value >= 0 else "#EF4444"),
                    pen=pg.mkPen("#22C55E" if value >= 0 else "#EF4444"),
                )
            )
            ticks.append((float(index), item.period_key))
        self.performance_plot.getAxis("bottom").setTicks([ticks])
        self.performance_plot.setLabel("left", f"PnL ({currency})")
        self.performance_plot.enableAutoRange()
        self.performance_plot.setXRange(-0.8, max(len(ordered) - 0.2, 0.8), padding=0)
        self.performance_message.setText(
            self._language.text("dashboard.performance.realized_scope").format(
                currency=currency,
                count=sum(item.event_count for item in ordered),
            )
        )

    def _clear_performance_plot(self) -> None:
        self.performance_plot.clear()
        self.performance_plot.getAxis("bottom").setTicks([[]])


class _KpiCard(QtWidgets.QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(0, 0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        self.setProperty("role", "panel")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        self.title = QtWidgets.QLabel()
        self.title.setProperty("role", "muted")
        self.value = QtWidgets.QLabel("N/A")
        value_font = self.value.font()
        value_font.setPointSize(12)
        value_font.setBold(True)
        self.value.setFont(value_font)
        for label in (self.title, self.value):
            label.setMinimumWidth(0)
            label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        layout.addWidget(self.title)
        layout.addWidget(self.value)

    def set_title(self, title: str) -> None:
        self.title.setText(title)

    def set_value(self, value: str) -> None:
        self.value.setText(value)


def _amount(amount: Amount | None) -> str:
    if amount is None or amount.value is None:
        return "N/A"
    marker = "~" if amount.estimate else ""
    return f"{marker}{format(amount.value, 'f')} {amount.currency.upper()}"


def _period_pnl(snapshot: DashboardVM, period: PnlPeriod) -> str:
    key = _period_key(snapshot.generated_at_utc, period)
    amounts = [
        item.amount
        for item in snapshot.realized_pnl
        if item.period is period and item.period_key == key
    ]
    if not amounts:
        return "N/A"
    return " · ".join(_amount(amount) for amount in amounts)


def _period_key(timestamp: datetime, period: PnlPeriod) -> str:
    if period is PnlPeriod.DAY:
        return timestamp.strftime("%Y-%m-%d")
    if period is PnlPeriod.WEEK:
        calendar = timestamp.isocalendar()
        return f"{calendar.year}-W{calendar.week:02d}"
    if period is PnlPeriod.MONTH:
        return timestamp.strftime("%Y-%m")
    return timestamp.strftime("%Y")


def _utc_text(timestamp: datetime) -> str:
    return timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
