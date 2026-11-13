"""Read-only separation of Paper positions and unavailable broker order data."""

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.app.projections.dashboard import DashboardVM
from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
from trading_ig_assistant.ui.models.position_table_model import PositionTableModel
from trading_ig_assistant.ui.shell.page_specs import PAGE_SPEC_BY_KEY


class PositionsPage(QtWidgets.QWidget):
    paper_save_requested = QtCore.pyqtSignal()
    paper_restore_requested = QtCore.pyqtSignal()
    paper_stop_requested = QtCore.pyqtSignal(str, str)
    paper_close_requested = QtCore.pyqtSignal(str)

    def __init__(self, language: LanguageManager) -> None:
        super().__init__()
        self._language = language
        self._snapshot: DashboardVM | None = None
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        self.title = QtWidgets.QLabel()
        font = self.title.font()
        font.setPointSize(16)
        font.setBold(True)
        self.title.setFont(font)
        layout.addWidget(self.title)
        self.safety = QtWidgets.QLabel()
        self.safety.setWordWrap(True)
        self.safety.setProperty("role", "muted")
        layout.addWidget(self.safety)
        self.tabs = QtWidgets.QTabWidget()
        (
            self.open_panel,
            self.open_table,
            self.open_model,
            self.open_empty,
        ) = self._position_panel()
        self.tabs.addTab(self.open_panel, "")
        self._messages: list[QtWidgets.QLabel] = []
        for _key in PAGE_SPEC_BY_KEY["positions"].tab_keys[1:3]:
            self.tabs.addTab(self._message_panel(), "")
        (
            self.paper_panel,
            self.paper_table,
            self.paper_model,
            self.paper_empty,
        ) = self._position_panel()
        self._add_paper_persistence_controls()
        self.tabs.addTab(self.paper_panel, "")
        self.tabs.addTab(self._message_panel(), "")
        layout.addWidget(self.tabs, stretch=1)
        self.retranslate_ui()

    def _add_paper_persistence_controls(self) -> None:
        controls = QtWidgets.QWidget()
        controls_layout = QtWidgets.QGridLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        self.paper_save_button = QtWidgets.QPushButton()
        self.paper_restore_button = QtWidgets.QPushButton()
        self.paper_stop_button = QtWidgets.QPushButton()
        self.paper_close_button = QtWidgets.QPushButton()
        self.paper_save_button.clicked.connect(self.paper_save_requested)
        self.paper_restore_button.clicked.connect(self.paper_restore_requested)
        self.paper_stop_button.clicked.connect(self._request_paper_stop)
        self.paper_close_button.clicked.connect(self._request_paper_close)
        self.paper_table.selectionModel().selectionChanged.connect(
            self._update_paper_action_state
        )
        controls_layout.addWidget(self.paper_save_button, 0, 0)
        controls_layout.addWidget(self.paper_restore_button, 0, 1)
        controls_layout.addWidget(self.paper_stop_button, 1, 0)
        controls_layout.addWidget(self.paper_close_button, 1, 1)
        controls_layout.setColumnStretch(2, 1)
        panel_layout = self.paper_panel.layout()
        if isinstance(panel_layout, QtWidgets.QVBoxLayout):
            panel_layout.insertWidget(0, controls)

    def _position_panel(
        self,
    ) -> tuple[
        QtWidgets.QWidget,
        QtWidgets.QTableView,
        PositionTableModel,
        QtWidgets.QLabel,
    ]:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        model = PositionTableModel(self._language)
        table = QtWidgets.QTableView()
        table.setModel(model)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table, stretch=1)
        empty = QtWidgets.QLabel()
        empty.setAlignment(QtCore.Qt.AlignCenter)
        empty.setProperty("role", "muted")
        layout.addWidget(empty)
        return panel, table, model, empty

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
        for model in (self.open_model, self.paper_model):
            model.set_rows(snapshot.open_positions)
        self._refresh()

    def retranslate_ui(self) -> None:
        self.title.setText(self._language.text("nav.positions"))
        self.safety.setText(self._language.text("positions.safety"))
        spec = PAGE_SPEC_BY_KEY["positions"]
        for index, key in enumerate(spec.tab_keys):
            self.tabs.setTabText(index, self._language.text(key))
        for model in (self.open_model, self.paper_model):
            model.retranslate_ui()
        message_keys = (
            "positions.pending_unavailable",
            "positions.order_history_unavailable",
            "positions.alerts_empty",
        )
        for message, key in zip(self._messages, message_keys, strict=True):
            message.setText(self._language.text(key))
        self.paper_save_button.setText(self._language.text("paper.save"))
        self.paper_restore_button.setText(self._language.text("paper.restore"))
        self.paper_stop_button.setText(self._language.text("paper.stop"))
        self.paper_close_button.setText(self._language.text("paper.close"))
        self.paper_save_button.setToolTip(self._language.text("paper.local_only"))
        self.paper_restore_button.setToolTip(self._language.text("paper.local_only"))
        self.paper_stop_button.setToolTip(self._language.text("paper.local_only"))
        self.paper_close_button.setToolTip(self._language.text("paper.local_only"))
        self._refresh()

    def _refresh(self) -> None:
        empty = self._snapshot is None or not self._snapshot.open_positions
        text = self._language.text("positions.paper_empty")
        for label in (self.open_empty, self.paper_empty):
            label.setText(text)
            label.setVisible(empty)
        self._update_paper_action_state()

    def _selected_paper_position_id(self) -> str | None:
        rows = self.paper_table.selectionModel().selectedRows()
        if not rows:
            return None
        value = self.paper_model.data(rows[0], QtCore.Qt.UserRole)
        return str(value) if value else None

    @QtCore.pyqtSlot()
    def _request_paper_stop(self) -> None:
        position_id = self._selected_paper_position_id()
        if position_id is None:
            return
        value, accepted = QtWidgets.QInputDialog.getText(
            self,
            self._language.text("paper.stop_title"),
            self._language.text("paper.stop_question"),
        )
        if accepted and value.strip():
            self.paper_stop_requested.emit(position_id, value.strip())

    @QtCore.pyqtSlot()
    def _request_paper_close(self) -> None:
        position_id = self._selected_paper_position_id()
        if position_id is not None:
            self.paper_close_requested.emit(position_id)

    @QtCore.pyqtSlot()
    def _update_paper_action_state(self, *_args: object) -> None:
        enabled = self._selected_paper_position_id() is not None
        self.paper_stop_button.setEnabled(enabled)
        self.paper_close_button.setEnabled(enabled)
