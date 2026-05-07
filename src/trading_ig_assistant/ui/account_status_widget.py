"""Account summary ribbon shown after read-only IG account retrieval."""

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.domain.instruments import Account
from trading_ig_assistant.utils.redaction import mask_identifier


class AccountStatusRibbonWidget(QtWidgets.QWidget):
    connect_requested = QtCore.pyqtSignal(object)
    settings_requested = QtCore.pyqtSignal()
    account_selected = QtCore.pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._accounts: list[Account] = []
        self._current_account_id: str | None = None
        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setContentsMargins(8, 4, 8, 6)
        self._layout.setSpacing(8)
        self._render()

    def set_accounts(self, accounts: list[Account], current_account_id: str | None) -> None:
        self._accounts = list(accounts)
        self._current_account_id = current_account_id
        self._render()

    def _render(self) -> None:
        self._clear()

        self._layout.addWidget(self._build_connect_button("Connect live", IGEnvironment.LIVE))
        self._layout.addWidget(self._build_connect_button("Connect demo", IGEnvironment.DEMO))
        self._layout.addWidget(self._build_settings_button())

        if not self._accounts:
            self._layout.addWidget(self._build_plain_label("IG account: not connected"))
            self._layout.addStretch(1)
            return

        selected = _select_current_account(self._accounts, self._current_account_id)
        self._layout.addWidget(self._build_account_dropdown(selected.account_id))
        self._layout.addWidget(
            self._build_chip("Valeur du compte", _money(selected.balance, selected.currency))
        )
        self._layout.addWidget(
            self._build_chip("Fonds disponibles", _money(selected.available, selected.currency))
        )
        self._layout.addWidget(
            self._build_chip("Gain/Pertes", _money(selected.profit_loss, selected.currency))
        )
        self._layout.addWidget(
            self._build_chip("Couverture", _money(selected.deposit, selected.currency))
        )
        self._layout.addStretch(1)

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _build_plain_label(self, text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setStyleSheet("QLabel { color: #4f5965; font-weight: 600; }")
        return label

    def _build_connect_button(
        self,
        text: str,
        environment: IGEnvironment,
    ) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(text)
        button.clicked.connect(lambda: self.connect_requested.emit(environment))
        return button

    def _build_settings_button(self) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton("Settings")
        button.clicked.connect(self.settings_requested.emit)
        return button

    def _build_account_dropdown(self, current_account_id: str) -> QtWidgets.QComboBox:
        combo = QtWidgets.QComboBox()
        for account in self._accounts:
            label = (
                f"{account.account_name or 'IG account'} "
                f"({account.account_type or 'type unknown'}, {mask_identifier(account.account_id)})"
            )
            combo.addItem(label, account.account_id)
            if account.account_id == current_account_id:
                combo.setCurrentIndex(combo.count() - 1)
        combo.currentIndexChanged.connect(lambda _index: self._account_selected(combo))
        return combo

    def _account_selected(self, combo: QtWidgets.QComboBox) -> None:
        account_id = combo.currentData()
        self._current_account_id = account_id
        self.account_selected.emit(account_id)
        self._render()

    def _build_chip(self, label: str, value: str) -> QtWidgets.QLabel:
        chip = QtWidgets.QLabel(f"{label}: {value}")
        chip.setStyleSheet(
            "QLabel {"
            "color: #203040;"
            "background: #e9f0f7;"
            "border: 1px solid #c6d3df;"
            "border-radius: 9px;"
            "padding: 4px 9px;"
            "font-weight: 600;"
            "}"
        )
        return chip


def _select_current_account(accounts: list[Account], current_account_id: str | None) -> Account:
    for account in accounts:
        if account.account_id == current_account_id:
            return account
    for account in accounts:
        if account.preferred:
            return account
    return accounts[0]


def _money(value: float | None, currency: str | None) -> str:
    if value is None:
        return "unknown"
    suffix = f" {currency}" if currency else ""
    return f"{value:,.2f}{suffix}"
