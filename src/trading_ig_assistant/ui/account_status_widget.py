"""Account summary ribbon shown after read-only IG account retrieval."""

from __future__ import annotations

from PyQt5 import QtWidgets

from trading_ig_assistant.domain.instruments import Account
from trading_ig_assistant.ui.settings_view import mask_identifier


class AccountStatusRibbonWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setContentsMargins(8, 4, 8, 6)
        self._layout.setSpacing(8)
        self._placeholder = QtWidgets.QLabel("IG account: not connected")
        self._placeholder.setStyleSheet("QLabel { color: #4f5965; font-weight: 600; }")
        self._layout.addWidget(self._placeholder)
        self._layout.addStretch(1)

    def set_accounts(self, accounts: list[Account], current_account_id: str | None) -> None:
        self._clear()
        if not accounts:
            self._layout.addWidget(self._build_plain_label("IG account: no account returned"))
            self._layout.addStretch(1)
            return

        selected = _select_current_account(accounts, current_account_id)
        self._layout.addWidget(
            self._build_chip(
                "Account",
                (
                    f"{selected.account_name or 'IG account'} "
                    f"({selected.account_type or 'type unknown'}, "
                    f"{mask_identifier(selected.account_id)})"
                ),
            )
        )
        self._layout.addWidget(self._build_chip("Currency", selected.currency or "unknown"))
        self._layout.addWidget(
            self._build_chip("Balance", _money(selected.balance, selected.currency))
        )
        self._layout.addWidget(
            self._build_chip("Available", _money(selected.available, selected.currency))
        )
        self._layout.addWidget(
            self._build_chip("Deposit", _money(selected.deposit, selected.currency))
        )
        self._layout.addWidget(
            self._build_chip("P/L", _money(selected.profit_loss, selected.currency))
        )
        self._layout.addWidget(self._build_chip("Accounts", str(len(accounts))))
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
