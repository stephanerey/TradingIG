"""Account summary ribbon shown after read-only IG account retrieval."""

from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.domain.instruments import Account
from trading_ig_assistant.utils.redaction import mask_identifier


class AccountStatusRibbonWidget(QtWidgets.QWidget):
    connect_requested = QtCore.pyqtSignal(object)
    disconnect_requested = QtCore.pyqtSignal()
    settings_requested = QtCore.pyqtSignal()
    account_selected = QtCore.pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._accounts: list[Account] = []
        self._current_account_id: str | None = None
        self._connected = False
        self._environment = IGEnvironment.LIVE
        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setContentsMargins(8, 4, 8, 6)
        self._layout.setSpacing(8)
        self._render()

    def set_accounts(
        self,
        accounts: list[Account],
        current_account_id: str | None,
        environment: IGEnvironment,
        *,
        connected: bool = False,
    ) -> None:
        self._accounts = list(accounts)
        self._current_account_id = current_account_id
        self._environment = environment
        self._connected = connected
        self._render()

    def set_disconnected(self) -> None:
        self._accounts = []
        self._current_account_id = None
        self._connected = False
        self._render()

    def _render(self) -> None:
        self._clear()

        self._layout.addWidget(self._build_environment_dropdown())
        self._layout.addWidget(self._build_connection_toggle())
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

    def _build_environment_dropdown(self) -> QtWidgets.QComboBox:
        combo = QtWidgets.QComboBox()
        combo.addItem("live", IGEnvironment.LIVE)
        combo.addItem("demo", IGEnvironment.DEMO)
        combo.setCurrentIndex(0 if self._environment == IGEnvironment.LIVE else 1)
        combo.setMaximumWidth(85)
        combo.currentIndexChanged.connect(lambda _index: self._set_environment(combo))
        return combo

    def _set_environment(self, combo: QtWidgets.QComboBox) -> None:
        self._environment = combo.currentData()

    def _build_connection_toggle(self) -> QtWidgets.QPushButton:
        button = QtWidgets.QToolButton()
        icon_type = (
            QtWidgets.QStyle.SP_MediaStop
            if self._connected
            else QtWidgets.QStyle.SP_MediaPlay
        )
        button.setIcon(self.style().standardIcon(icon_type))
        button.setIconSize(QtCore.QSize(20, 20))
        button.setToolTip("Disconnect" if self._connected else "Connect")
        button.setFixedSize(34, 34)
        button.clicked.connect(self._toggle_connection)
        return button

    def _build_settings_button(self) -> QtWidgets.QPushButton:
        button = QtWidgets.QToolButton()
        button.setIcon(_settings_icon())
        button.setIconSize(QtCore.QSize(21, 21))
        button.setToolTip("Settings")
        button.setFixedSize(34, 34)
        button.clicked.connect(self.settings_requested.emit)
        return button

    def _toggle_connection(self) -> None:
        if self._connected:
            self.disconnect_requested.emit()
        else:
            self.connect_requested.emit(self._environment)

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


def _settings_icon() -> QtGui.QIcon:
    pixmap = QtGui.QPixmap(24, 24)
    pixmap.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    pen = QtGui.QPen(QtGui.QColor("#203040"), 2)
    painter.setPen(pen)
    painter.setBrush(QtGui.QBrush(QtGui.QColor("#e9f0f7")))

    center = QtCore.QPointF(12, 12)
    for angle in range(0, 360, 45):
        line = QtCore.QLineF(center, QtCore.QPointF(12, 3))
        line.setAngle(angle)
        painter.drawLine(line.pointAt(0.68), line.pointAt(1.0))

    painter.drawEllipse(QtCore.QPointF(12, 12), 6.5, 6.5)
    painter.setBrush(QtGui.QBrush(QtGui.QColor("#203040")))
    painter.drawEllipse(QtCore.QPointF(12, 12), 2.2, 2.2)
    painter.end()
    return QtGui.QIcon(pixmap)
