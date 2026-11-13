"""Projection and explicit local controls for the volatile Paper session."""

from __future__ import annotations

from decimal import Decimal

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.domain.adapter_contracts import ExecutionResult, ExecutionStatus
from trading_ig_assistant.domain.journal import JournalEvent
from trading_ig_assistant.domain.positions import PaperPositionStatus
from trading_ig_assistant.services.paper_session import (
    PaperOrderRecord,
    PaperPositionSnapshot,
)


class PaperPortfolioWidget(QtWidgets.QWidget):
    """Display Paper state and emit explicit actions that remain local to the session."""

    stop_update_requested = QtCore.pyqtSignal(str, object)
    close_requested = QtCore.pyqtSignal(str)
    save_requested = QtCore.pyqtSignal()
    restore_requested = QtCore.pyqtSignal()

    @property
    def position_snapshots(self) -> tuple[PaperPositionSnapshot, ...]:
        return self._position_snapshots

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)

        banner = QtWidgets.QLabel(
            "SESSION DE SIMULATION LOCALE — aucune transmission à IG; "
            "persistance uniquement sur action explicite"
        )
        banner.setWordWrap(True)
        banner.setAlignment(QtCore.Qt.AlignCenter)
        banner.setStyleSheet(
            "QLabel { background: #e9f3ff; color: #153a5b; padding: 6px; font-weight: 700; }"
        )
        layout.addWidget(banner)

        self.summary = QtWidgets.QLabel("0 position · 0 ordre · 0 événement")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        persistence_actions = QtWidgets.QHBoxLayout()
        self.save_session_button = QtWidgets.QPushButton("Sauvegarder la simulation")
        self.restore_session_button = QtWidgets.QPushButton("Restaurer la dernière session")
        persistence_actions.addWidget(self.save_session_button)
        persistence_actions.addWidget(self.restore_session_button)
        layout.addLayout(persistence_actions)
        self.persistence_result = QtWidgets.QLabel(
            "Aucune sauvegarde ou restauration demandée pendant cette exécution."
        )
        self.persistence_result.setWordWrap(True)
        layout.addWidget(self.persistence_result)

        self.tabs = QtWidgets.QTabWidget()
        self.positions_table = _table(
            "paperPositionsTable",
            (
                "Statut",
                "Produit",
                "Sens",
                "Taille",
                "Entrée",
                "Prix",
                "P&L net",
                "Stop",
                "Objectif",
                "KO",
            ),
        )
        self.orders_table = _table(
            "paperOrdersTable",
            ("Heure UTC", "Intention", "Produit", "Sens", "Taille", "Statut", "Détail"),
        )
        self.journal_table = _table(
            "paperJournalTable",
            ("Heure UTC", "Événement", "Produit", "Corrélation", "P&L", "Devise"),
        )
        self.tabs.addTab(self.positions_table, "Positions")
        self.tabs.addTab(self.orders_table, "Ordres")
        self.tabs.addTab(self.journal_table, "Journal")
        layout.addWidget(self.tabs, stretch=1)

        actions = QtWidgets.QGroupBox("Actions sur la position simulée sélectionnée")
        actions_layout = QtWidgets.QVBoxLayout(actions)
        self.action_help = QtWidgets.QLabel(
            "Simulation locale uniquement. Un stop peut être resserré, jamais élargi. "
            "Les prix et P&L sont actualisés à la réception des cotations et à l'ouverture "
            "de cet onglet ; leur fraîcheur peut changer entre deux mises à jour."
        )
        self.action_help.setWordWrap(True)
        actions_layout.addWidget(self.action_help)

        stop_form = QtWidgets.QFormLayout()
        self.stop_value = QtWidgets.QDoubleSpinBox()
        self.stop_value.setDecimals(6)
        self.stop_value.setRange(0.000001, 1_000_000_000)
        self.stop_value.setGroupSeparatorShown(True)
        stop_form.addRow("Nouveau stop absolu", self.stop_value)
        actions_layout.addLayout(stop_form)

        self.tighten_stop_button = QtWidgets.QPushButton("Resserrer le stop simulé")
        self.close_position_button = QtWidgets.QPushButton(
            "Clôturer la position simulée sélectionnée"
        )
        self.tighten_stop_button.setEnabled(False)
        self.close_position_button.setEnabled(False)
        actions_layout.addWidget(self.tighten_stop_button)
        actions_layout.addWidget(self.close_position_button)

        self.action_result = QtWidgets.QLabel("Sélectionnez une position ouverte.")
        self.action_result.setWordWrap(True)
        actions_layout.addWidget(self.action_result)
        layout.addWidget(actions)

        self._position_snapshots: tuple[PaperPositionSnapshot, ...] = ()
        self._action_position_id: str | None = None
        self.positions_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.positions_table.itemSelectionChanged.connect(self._sync_action_state)
        self.tighten_stop_button.clicked.connect(self._request_stop_update)
        self.close_position_button.clicked.connect(self._request_close)
        self.save_session_button.clicked.connect(self.save_requested)
        self.restore_session_button.clicked.connect(self.restore_requested)

    def set_session_state(
        self,
        positions: tuple[PaperPositionSnapshot, ...],
        orders: tuple[PaperOrderRecord, ...],
        events: tuple[JournalEvent, ...],
    ) -> None:
        selected_id = self._selected_position_id()
        self._position_snapshots = positions
        self.positions_table.blockSignals(True)
        self._render_positions(positions)
        selected_row = next(
            (
                row
                for row, snapshot in enumerate(positions)
                if snapshot.position.position_id == selected_id
            ),
            None,
        )
        if selected_row is None:
            selected_row = next(
                (
                    row
                    for row, snapshot in enumerate(positions)
                    if snapshot.position.status is PaperPositionStatus.OPEN
                ),
                None,
            )
        if selected_row is not None:
            self.positions_table.selectRow(selected_row)
        self.positions_table.blockSignals(False)
        self._sync_action_state()
        self._render_orders(orders)
        self._render_events(events)
        open_count = sum(item.position.status.value == "open" for item in positions)
        self.summary.setText(
            f"{open_count} position ouverte · {len(orders)} ordre · {len(events)} événement"
        )

    def show_action_result(self, result: ExecutionResult) -> None:
        if result.status is ExecutionStatus.CONFIRMED:
            self.action_result.setText(
                f"CONFIRMÉ LOCALEMENT — {result.message or result.status.value}"
            )
            return
        self.action_result.setText(f"REFUSÉ — {result.message or result.status.value}")

    def show_persistence_result(self, message: str, *, error: bool = False) -> None:
        color = "#8b1e1e" if error else "#153a5b"
        self.persistence_result.setStyleSheet(f"QLabel {{ color: {color}; }}")
        self.persistence_result.setText(message)

    @QtCore.pyqtSlot()
    def _request_stop_update(self) -> None:
        snapshot = self._selected_open_snapshot()
        if snapshot is None:
            return
        self.stop_update_requested.emit(
            snapshot.position.position_id,
            Decimal(str(self.stop_value.value())),
        )

    @QtCore.pyqtSlot()
    def _request_close(self) -> None:
        snapshot = self._selected_open_snapshot()
        if snapshot is not None:
            self.close_requested.emit(snapshot.position.position_id)

    @QtCore.pyqtSlot()
    def _sync_action_state(self) -> None:
        snapshot = self._selected_open_snapshot()
        enabled = snapshot is not None
        self.tighten_stop_button.setEnabled(enabled)
        self.close_position_button.setEnabled(enabled)
        if snapshot is None:
            self._action_position_id = None
            return
        position = snapshot.position
        if self._action_position_id != position.position_id:
            self._action_position_id = position.position_id
            if position.current_stop is not None:
                self.stop_value.setValue(float(position.current_stop))

    def _selected_position_id(self) -> str | None:
        row = self.positions_table.currentRow()
        if 0 <= row < len(self._position_snapshots):
            return self._position_snapshots[row].position.position_id
        return None

    def _selected_open_snapshot(self) -> PaperPositionSnapshot | None:
        row = self.positions_table.currentRow()
        if not 0 <= row < len(self._position_snapshots):
            return None
        snapshot = self._position_snapshots[row]
        if snapshot.position.status is not PaperPositionStatus.OPEN:
            return None
        return snapshot

    def _render_positions(self, snapshots: tuple[PaperPositionSnapshot, ...]) -> None:
        self.positions_table.setRowCount(len(snapshots))
        for row, snapshot in enumerate(snapshots):
            position = snapshot.position
            values = (
                position.status.value,
                position.product_id,
                position.direction.value,
                _decimal(position.quantity),
                _decimal(position.entry_price),
                _decimal(snapshot.mark_price),
                _decimal(snapshot.net_pnl),
                _decimal(position.current_stop),
                _decimal(position.target),
                _decimal(position.knockout),
            )
            _set_row(self.positions_table, row, values)
        self.positions_table.resizeColumnsToContents()

    def _render_orders(self, records: tuple[PaperOrderRecord, ...]) -> None:
        self.orders_table.setRowCount(len(records))
        for row, record in enumerate(records):
            intent = record.submission.ticket.intent
            result = record.outcome.execution_result
            values = (
                record.submitted_at_utc.strftime("%H:%M:%S"),
                intent.intent_id,
                intent.product_id,
                intent.direction.value,
                _decimal(intent.quantity),
                result.status.value,
                _simulation_label(result.message or ""),
            )
            _set_row(self.orders_table, row, values)
        self.orders_table.resizeColumnsToContents()

    def _render_events(self, events: tuple[JournalEvent, ...]) -> None:
        self.journal_table.setRowCount(len(events))
        for row, event in enumerate(events):
            values = (
                event.timestamp_utc.strftime("%H:%M:%S"),
                _simulation_label(event.event_type),
                event.instrument_id or "",
                event.correlation_id,
                _decimal(event.pnl_amount),
                event.pnl_currency or "",
            )
            _set_row(self.journal_table, row, values)
        self.journal_table.resizeColumnsToContents()


def _table(name: str, columns: tuple[str, ...]) -> QtWidgets.QTableWidget:
    table = QtWidgets.QTableWidget(0, len(columns))
    table.setObjectName(name)
    table.setHorizontalHeaderLabels(columns)
    table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    table.setAlternatingRowColors(True)
    table.horizontalHeader().setStretchLastSection(True)
    return table


def _set_row(table: QtWidgets.QTableWidget, row: int, values: tuple[str, ...]) -> None:
    for column, value in enumerate(values):
        item = QtWidgets.QTableWidgetItem(value)
        if column >= 3:
            item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        table.setItem(row, column, item)


def _decimal(value: Decimal | None) -> str:
    if value is None:
        return "—"
    return format(value.quantize(Decimal("0.0001")), "f").rstrip("0").rstrip(".") or "0"


def _simulation_label(value: str) -> str:
    return (
        value.replace("PAPER_", "SIMULATION_")
        .replace("PAPER-", "SIMULATION-")
        .replace("Paper", "simulation")
    )
