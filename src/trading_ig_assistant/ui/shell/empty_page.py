"""Honest empty-state page used until a real projection is wired."""

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
from trading_ig_assistant.ui.shell.page_specs import PageSpec


class EmptyPage(QtWidgets.QWidget):
    def __init__(self, spec: PageSpec, language: LanguageManager) -> None:
        super().__init__()
        self._spec = spec
        self._language = language
        self._tabs: list[tuple[QtWidgets.QWidget, str, QtWidgets.QLabel, QtWidgets.QLabel]] = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        self.title_label = QtWidgets.QLabel()
        title_font = self.title_label.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setDocumentMode(True)
        for tab_key in spec.tab_keys:
            panel = QtWidgets.QFrame()
            panel.setProperty("role", "panel")
            panel_layout = QtWidgets.QVBoxLayout(panel)
            body = QtWidgets.QLabel()
            body.setWordWrap(True)
            body.setAlignment(QtCore.Qt.AlignCenter)
            body.setProperty("role", "secondary")
            network_note = QtWidgets.QLabel()
            network_note.setWordWrap(True)
            network_note.setAlignment(QtCore.Qt.AlignCenter)
            network_note.setProperty("role", "muted")
            panel_layout.addStretch(1)
            panel_layout.addWidget(body)
            panel_layout.addWidget(network_note)
            panel_layout.addStretch(1)
            self.tabs.addTab(panel, "")
            self._tabs.append((panel, tab_key, body, network_note))
        layout.addWidget(self.tabs, stretch=1)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.title_label.setText(self._language.text(self._spec.title_key))
        for index, (_panel, tab_key, body, network_note) in enumerate(self._tabs):
            self.tabs.setTabText(index, self._language.text(tab_key))
            body.setText(self._language.text("page.empty.body"))
            network_note.setText(self._language.text("page.empty.no_network"))
