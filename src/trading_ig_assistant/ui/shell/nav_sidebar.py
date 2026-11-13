"""Persistent collapsible navigation for the GUI V2 shell."""

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
from trading_ig_assistant.ui.shell.page_specs import PAGE_SPECS


class NavSidebar(QtWidgets.QWidget):
    page_selected = QtCore.pyqtSignal(str)
    collapsed_changed = QtCore.pyqtSignal(bool)

    def __init__(self, language: LanguageManager, *, collapsed: bool = False) -> None:
        super().__init__()
        self.setObjectName("NavSidebar")
        self._language = language
        self._collapsed = collapsed
        self._buttons: dict[str, QtWidgets.QPushButton] = {}

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(6)
        self._group = QtWidgets.QButtonGroup(self)
        self._group.setExclusive(True)
        for spec in PAGE_SPECS:
            button = QtWidgets.QPushButton()
            button.setCheckable(True)
            button.setMinimumHeight(36)
            button.clicked.connect(lambda _checked, key=spec.key: self.page_selected.emit(key))
            self._group.addButton(button)
            self._buttons[spec.key] = button
            layout.addWidget(button)
        layout.addStretch(1)
        self.collapse_button = QtWidgets.QPushButton()
        self.collapse_button.clicked.connect(self.toggle_collapsed)
        layout.addWidget(self.collapse_button)
        self.set_collapsed(collapsed, emit=False)

    @property
    def collapsed(self) -> bool:
        return self._collapsed

    def select_page(self, key: str) -> None:
        button = self._buttons.get(key)
        if button is not None:
            button.setChecked(True)

    def toggle_collapsed(self) -> None:
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool, *, emit: bool = True) -> None:
        self._collapsed = bool(collapsed)
        self.setFixedWidth(64 if self._collapsed else 216)
        self.retranslate_ui()
        if emit:
            self.collapsed_changed.emit(self._collapsed)

    def retranslate_ui(self) -> None:
        for index, spec in enumerate(PAGE_SPECS, start=1):
            label = self._language.text(spec.title_key)
            button = self._buttons[spec.key]
            button.setText(str(index) if self._collapsed else label)
            button.setToolTip(label)
        collapse_key = "nav.expand" if self._collapsed else "nav.collapse"
        collapse_label = self._language.text(collapse_key)
        self.collapse_button.setText("»" if self._collapsed else collapse_label)
        self.collapse_button.setToolTip(collapse_label)
