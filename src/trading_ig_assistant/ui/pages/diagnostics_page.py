"""Observed service health for GUI V2 without active probing."""

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.app.projections.health import HealthServiceVM
from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
from trading_ig_assistant.ui.shell.page_specs import PAGE_SPEC_BY_KEY


class DiagnosticsPage(QtWidgets.QWidget):
    def __init__(self, language: LanguageManager) -> None:
        super().__init__()
        self._language = language
        self._health: tuple[HealthServiceVM, ...] = ()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        self.title = QtWidgets.QLabel()
        font = self.title.font()
        font.setPointSize(16)
        font.setBold(True)
        self.title.setFont(font)
        layout.addWidget(self.title)
        self.tabs = QtWidgets.QTabWidget()
        health_panel = QtWidgets.QWidget()
        health_layout = QtWidgets.QVBoxLayout(health_panel)
        self.health_table = QtWidgets.QTableWidget(0, 5)
        self.health_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.health_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.health_table.horizontalHeader().setStretchLastSection(True)
        health_layout.addWidget(self.health_table)
        self.tabs.addTab(health_panel, "")
        self._messages: list[QtWidgets.QLabel] = []
        for _key in PAGE_SPEC_BY_KEY["diagnostics"].tab_keys[1:]:
            panel = QtWidgets.QWidget()
            panel_layout = QtWidgets.QVBoxLayout(panel)
            message = QtWidgets.QLabel()
            message.setAlignment(QtCore.Qt.AlignCenter)
            message.setWordWrap(True)
            panel_layout.addWidget(message)
            self._messages.append(message)
            self.tabs.addTab(panel, "")
        layout.addWidget(self.tabs, stretch=1)
        self.retranslate_ui()

    def set_health(self, snapshots: tuple[HealthServiceVM, ...]) -> None:
        self._health = snapshots
        self._refresh()

    def retranslate_ui(self) -> None:
        self.title.setText(self._language.text("nav.diagnostics"))
        spec = PAGE_SPEC_BY_KEY["diagnostics"]
        for index, key in enumerate(spec.tab_keys):
            self.tabs.setTabText(index, self._language.text(key))
        self.health_table.setHorizontalHeaderLabels(
            tuple(
                self._language.text(key)
                for key in (
                    "diagnostics.service",
                    "diagnostics.state",
                    "diagnostics.summary",
                    "diagnostics.observed",
                    "diagnostics.reasons",
                )
            )
        )
        for message in self._messages:
            message.setText(self._language.text("diagnostics.no_active_probe"))
        self._refresh()

    def _refresh(self) -> None:
        self.health_table.setRowCount(len(self._health))
        for row_index, snapshot in enumerate(self._health):
            values = (
                self._service_name(snapshot.service_id),
                self._language.text(f"diagnostics.status.{snapshot.status.value}"),
                self._summary(snapshot.summary),
                (
                    snapshot.observed_at_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
                    if snapshot.observed_at_utc is not None
                    else "N/A"
                ),
                ", ".join(snapshot.reason_codes) or "N/A",
            )
            for column, value in enumerate(values):
                self.health_table.setItem(row_index, column, QtWidgets.QTableWidgetItem(value))

    def _service_name(self, service_id: str) -> str:
        known = {
            "ig-rest",
            "ig-streaming",
            "openai",
            "paper-sqlite",
            "official-news",
        }
        if service_id not in known:
            return service_id
        return self._language.text(f"diagnostics.service.{service_id}")

    def _summary(self, summary: str) -> str:
        key = summary.strip().lower().replace(" ", "_")
        known = {
            "connected",
            "connecting",
            "disconnected",
            "live",
            "not_configured",
            "empty_session",
            "unsaved_changes",
            "snapshot_saved",
            "error",
            "metadata_available",
            "not_collected",
            "configured",
            "last_request_available",
            "last_request_stale",
            "ready",
            "running",
        }
        if key not in known:
            return summary
        return self._language.text(f"diagnostics.summary.{key}")
