"""Persistent read-only account and runtime status header."""

from __future__ import annotations

from decimal import Decimal

from PyQt5 import QtCore, QtGui, QtWidgets

from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.app.projections.account import AccountHeaderVM
from trading_ig_assistant.app.projections.common import Amount
from trading_ig_assistant.domain.instruments import Account
from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
from trading_ig_assistant.utils.redaction import mask_identifier


class _MetricCard(QtWidgets.QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setProperty("role", "accountMetric")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 7)
        layout.setSpacing(1)
        self.title = QtWidgets.QLabel()
        self.title.setProperty("role", "metricTitle")
        self.value = QtWidgets.QLabel("N/A")
        self.value.setProperty("role", "metricValue")
        self.value.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        self.setMinimumWidth(110)

    def set_amount(self, amount: Amount | None, *, pnl: bool = False) -> None:
        self.value.setText(_format_amount(amount))
        state = "unknown"
        if amount is not None and amount.value is not None:
            if pnl and amount.value > 0:
                state = "profit"
            elif pnl and amount.value < 0:
                state = "loss"
            else:
                state = "known"
        _set_dynamic_property(self.value, "state", state)


class AccountHeader(QtWidgets.QFrame):
    connect_demo_requested = QtCore.pyqtSignal()
    connect_live_requested = QtCore.pyqtSignal()
    disconnect_requested = QtCore.pyqtSignal()
    account_selected = QtCore.pyqtSignal(str)

    def __init__(self, language: LanguageManager) -> None:
        super().__init__()
        self.setProperty("role", "panel")
        self._language = language
        self._snapshot: AccountHeaderVM | None = None
        self._connection_controls_available = False
        self._busy = False
        self._accounts: tuple[Account, ...] = ()
        self._current_account_id: str | None = None
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(14)

        connection_panel = QtWidgets.QWidget()
        connection_layout = QtWidgets.QVBoxLayout(connection_panel)
        connection_layout.setContentsMargins(0, 0, 0, 0)
        connection_layout.setSpacing(4)
        self.identity_label = QtWidgets.QLabel("TradingIG")
        identity_font = self.identity_label.font()
        identity_font.setBold(True)
        self.identity_label.setFont(identity_font)
        connection_layout.addWidget(self.identity_label)

        controls = QtWidgets.QWidget()
        controls_layout = QtWidgets.QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(6)
        self.environment_combo = QtWidgets.QComboBox()
        self.environment_combo.setMinimumWidth(92)
        self.environment_combo.addItem("DEMO", IGEnvironment.DEMO.value)
        self.environment_combo.addItem("LIVE", IGEnvironment.LIVE.value)
        self.environment_combo.currentIndexChanged.connect(
            lambda _index: self._update_safety_text()
        )
        self.connect_button = QtWidgets.QPushButton()
        self.connect_button.setProperty("role", "connectionAction")
        self.connect_button.setFixedWidth(46)
        self.connect_button.setIconSize(QtCore.QSize(18, 18))
        self.connect_button.clicked.connect(self._handle_connection_action)
        controls_layout.addWidget(self.environment_combo)
        controls_layout.addWidget(self.connect_button)
        connection_layout.addWidget(controls)
        self._connection_controls = controls

        self.safety_label = QtWidgets.QLabel()
        self.safety_label.setProperty("role", "muted")
        self.safety_label.setMinimumWidth(0)
        self.safety_label.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Preferred,
        )
        connection_layout.addWidget(self.safety_label)

        self.account_combo = QtWidgets.QComboBox()
        self.account_combo.setMinimumWidth(220)
        self.account_combo.setMinimumContentsLength(12)
        self.account_combo.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Fixed,
        )
        self.account_combo.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        self.account_combo.currentIndexChanged.connect(self._emit_account_selection)
        connection_layout.addWidget(self.account_combo)

        self.data_label = QtWidgets.QLabel()
        self.data_label.setProperty("role", "secondary")
        self.ai_label = QtWidgets.QLabel()
        self.ai_label.setProperty("role", "secondary")
        for label in (self.data_label, self.ai_label):
            label.setMinimumWidth(0)
            label.setSizePolicy(
                QtWidgets.QSizePolicy.Ignored,
                QtWidgets.QSizePolicy.Preferred,
            )
        connection_layout.addWidget(self.data_label)
        connection_layout.addWidget(self.ai_label)
        layout.addWidget(connection_panel, stretch=2)

        account_panel = QtWidgets.QWidget()
        account_layout = QtWidgets.QGridLayout(account_panel)
        account_layout.setContentsMargins(0, 0, 0, 0)
        account_layout.setHorizontalSpacing(8)
        account_layout.setVerticalSpacing(5)
        self.account_label = QtWidgets.QLabel()
        self.environment_label = QtWidgets.QLabel()
        self.execution_label = QtWidgets.QLabel()
        self.account_label.setProperty("role", "accountIdentity")
        self.environment_label.setProperty("role", "secondary")
        self.execution_label.setProperty("role", "secondary")
        compressible_labels = (self.account_label, self.environment_label, self.execution_label)
        for label in compressible_labels:
            label.setMinimumWidth(0)
            label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        account_layout.addWidget(self.account_label, 0, 0, 1, 2)
        account_layout.addWidget(self.environment_label, 0, 2)
        account_layout.addWidget(self.execution_label, 0, 3)

        self.equity_card = _MetricCard()
        self.balance_card = _MetricCard()
        self.available_card = _MetricCard()
        self.pnl_card = _MetricCard()
        self._metric_cards = (
            self.equity_card,
            self.balance_card,
            self.available_card,
            self.pnl_card,
        )
        for column, card in enumerate(self._metric_cards):
            account_layout.addWidget(card, 1, column)
            account_layout.setColumnStretch(column, 1)
        layout.addWidget(account_panel, stretch=5)
        self.retranslate_ui()

    def set_connection_controls_available(self, available: bool) -> None:
        self._connection_controls_available = available
        self._connection_controls.setVisible(available)
        self._update_control_state()

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._update_control_state()

    def set_accounts(
        self,
        accounts: tuple[Account, ...],
        current_account_id: str | None,
    ) -> None:
        self._accounts = accounts
        self._current_account_id = current_account_id
        self._render_accounts()

    def _render_accounts(self) -> None:
        blocker = QtCore.QSignalBlocker(self.account_combo)
        self.account_combo.clear()
        selected_index = -1
        if not self._accounts:
            self.account_combo.addItem(
                self._language.text("header.account_connect_first"),
                None,
            )
        for account in self._accounts:
            environment = (
                (self._snapshot.ig_environment or "—").upper()
                if self._snapshot is not None
                else "—"
            )
            family = _account_family_label(
                self._language,
                account.account_type,
                account.account_name,
            )
            descriptor = _account_descriptor(environment, family, account)
            self.account_combo.addItem(descriptor, account.account_id)
            item_index = self.account_combo.count() - 1
            self.account_combo.setItemData(item_index, descriptor, QtCore.Qt.ToolTipRole)
            if account.account_id == self._current_account_id:
                selected_index = self.account_combo.count() - 1
        self.account_combo.setCurrentIndex(selected_index if selected_index >= 0 else 0)
        self.account_combo.setToolTip(self._language.text("header.account_selector_help"))
        del blocker
        self._update_control_state()

    def set_snapshot(self, snapshot: AccountHeaderVM) -> None:
        previous_environment = self._snapshot.ig_environment if self._snapshot is not None else None
        self._snapshot = snapshot
        if snapshot.ig_environment:
            index = self.environment_combo.findData(snapshot.ig_environment.lower())
            if index >= 0:
                self.environment_combo.setCurrentIndex(index)
        if snapshot.ig_environment != previous_environment and self._accounts:
            self._render_accounts()
        self._render_snapshot()

    def retranslate_ui(self) -> None:
        self.equity_card.title.setText(self._language.text("header.metric.equity"))
        self.balance_card.title.setText(self._language.text("header.metric.balance"))
        self.available_card.title.setText(self._language.text("header.metric.available"))
        self.pnl_card.title.setText(self._language.text("header.metric.pnl"))
        self._update_safety_text()
        self._render_accounts()
        self._render_snapshot()

    def _render_snapshot(self) -> None:
        snapshot = self._snapshot
        if snapshot is None:
            self.account_label.setText(
                f"{self._language.text('header.account')}: "
                f"{self._language.text('header.no_account')}"
            )
            self.environment_label.setText(f"{self._language.text('header.environment')}: —")
            self.execution_label.setText(
                f"{self._language.text('header.execution')}: "
                f"{self._language.text('status.analysis')}"
            )
            for card in self._metric_cards:
                card.set_amount(None)
            self.data_label.setText(
                f"{self._language.text('header.data')}: "
                f"{self._language.text('status.disconnected')}"
            )
            self.ai_label.setText(
                f"{self._language.text('header.ai')}: "
                f"{self._language.text('status.not_configured')}"
            )
            self._update_control_state()
            return
        selected_account = next(
            (account for account in self._accounts if account.account_id == snapshot.account_id),
            None,
        )
        family = _account_family_label(
            self._language,
            snapshot.product_account_type,
            selected_account.account_name if selected_account is not None else "",
        )
        environment = (snapshot.ig_environment or "—").upper()
        descriptor = (
            _account_descriptor(environment, family, selected_account)
            if selected_account is not None
            else f"{environment} · {family} · "
            f"{mask_identifier(snapshot.account_id) if snapshot.account_id else '—'}"
        )
        self.account_label.setText(f"{self._language.text('header.account')}: {descriptor}")
        self.account_label.setToolTip(descriptor)
        self.environment_label.setText(
            f"{self._language.text('header.environment')}: "
            f"{(snapshot.ig_environment or '—').upper()}"
        )
        execution_mode = (
            self._language.text("status.paper")
            if snapshot.execution_mode.upper() == "PAPER"
            else snapshot.execution_mode
        )
        self.execution_label.setText(
            f"{self._language.text('header.execution')}: {execution_mode}"
        )
        metrics = self._language.text("header.account_metrics").format(
            equity=_format_amount(snapshot.equity),
            balance=_format_amount(snapshot.account_balance),
            available=_format_amount(snapshot.available_funds),
            pnl=_format_amount(snapshot.account_profit_loss),
        )
        metrics_tooltip = self._language.text("header.account_metrics_tooltip").format(
            timestamp=snapshot.generated_at_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        self.equity_card.set_amount(snapshot.equity)
        self.balance_card.set_amount(snapshot.account_balance)
        self.available_card.set_amount(snapshot.available_funds)
        self.pnl_card.set_amount(snapshot.account_profit_loss, pnl=True)
        for card in self._metric_cards:
            card.setToolTip(f"{metrics}\n{metrics_tooltip}")
        self.data_label.setText(
            f"{self._language.text('header.data')}: "
            f"REST {snapshot.ig_rest_status} / STREAM {snapshot.ig_stream_status}"
        )
        self.ai_label.setText(
            f"{self._language.text('header.ai')}: "
            f"{self._language.text(f'status.ai.{snapshot.ai_status}')}"
        )
        self._update_control_state()

    @QtCore.pyqtSlot()
    def _handle_connection_action(self) -> None:
        if self._is_connected():
            self.disconnect_requested.emit()
            return
        environment = self.environment_combo.currentData()
        if environment == IGEnvironment.LIVE.value:
            self.connect_live_requested.emit()
        else:
            self.connect_demo_requested.emit()

    @QtCore.pyqtSlot(int)
    def _emit_account_selection(self, index: int) -> None:
        account_id = self.account_combo.itemData(index)
        if account_id:
            self.account_selected.emit(str(account_id))

    def _update_control_state(self) -> None:
        connected = self._is_connected()
        enabled = self._connection_controls_available and not self._busy
        self.environment_combo.setEnabled(enabled and not connected)
        self.connect_button.setEnabled(enabled)
        state = "busy" if self._busy else "connected" if connected else "disconnected"
        _set_dynamic_property(self.connect_button, "connectionState", state)
        if self._busy:
            self.connect_button.setIcon(QtGui.QIcon())
            self.connect_button.setText("…")
            self.connect_button.setAccessibleName(self._language.text("header.connecting"))
            self.connect_button.setToolTip(self._language.text("header.connecting"))
        elif connected:
            self.connect_button.setText("")
            self.connect_button.setIcon(_media_icon("stop"))
            self.connect_button.setAccessibleName(
                self._language.text("header.disconnect_action")
            )
            self.connect_button.setToolTip(self._language.text("header.connected_help"))
        else:
            self.connect_button.setText("")
            self.connect_button.setIcon(_media_icon("play"))
            self.connect_button.setAccessibleName(self._language.text("header.connect"))
            self.connect_button.setToolTip(self._language.text("header.connect_help"))
        self.account_combo.setEnabled(enabled and connected and self.account_combo.count() > 1)

    def _is_connected(self) -> bool:
        return bool(self._snapshot is not None and self._snapshot.ig_rest_status == "connected")

    def _update_safety_text(self) -> None:
        environment = (
            self._snapshot.ig_environment
            if self._is_connected() and self._snapshot is not None
            else self.environment_combo.currentData()
        )
        self.safety_label.setText(
            self._language.text("header.read_only_safety").format(
                environment=str(environment or "—").upper()
            )
        )


def _format_amount(amount: Amount | None) -> str:
    if amount is None or amount.value is None:
        return "N/A"
    value: Decimal = amount.value
    marker = "~" if amount.estimate else ""
    return f"{marker}{format(value, 'f')} {amount.currency.upper()}"


def _set_dynamic_property(widget: QtWidgets.QWidget, name: str, value: str) -> None:
    if widget.property(name) == value:
        return
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def _media_icon(kind: str) -> QtGui.QIcon:
    pixmap = QtGui.QPixmap(20, 20)
    pixmap.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.setPen(QtCore.Qt.NoPen)
    painter.setBrush(QtGui.QColor("#FFFFFF"))
    if kind == "play":
        painter.drawPolygon(
            QtGui.QPolygonF(
                (
                    QtCore.QPointF(6, 4),
                    QtCore.QPointF(16, 10),
                    QtCore.QPointF(6, 16),
                )
            )
        )
    else:
        painter.drawRoundedRect(QtCore.QRectF(5, 5, 10, 10), 1, 1)
    painter.end()
    return QtGui.QIcon(pixmap)


def _account_family_label(
    language: LanguageManager,
    account_type: str | None,
    account_name: str,
) -> str:
    normalized_type = (account_type or "").strip().upper()
    normalized_name = account_name.strip().lower()
    if normalized_type in {"OPTIONS", "OPTION", "BARRIER", "BARRIERS"} or any(
        token in normalized_name for token in ("barri", "option")
    ):
        return language.text("header.account_family_options")
    if normalized_type == "CFD" or "cfd" in normalized_name:
        return language.text("header.account_family_cfd")
    if normalized_type in {"SPREADBET", "SPREAD_BET", "SPREAD BET"}:
        return language.text("header.account_family_spreadbet")
    if normalized_type in {
        "PHYSICAL",
        "SHARE_DEALING",
        "SHAREDEALING",
        "STOCKBROKING",
    }:
        return language.text("header.account_family_shares")
    if normalized_type:
        return f"{language.text('header.account_family_unknown')} ({normalized_type})"
    return language.text("header.account_family_unknown")


def _account_descriptor(environment: str, family: str, account: Account) -> str:
    name = account.account_name.strip()
    parts = [environment, family]
    if name:
        parts.append(name)
    parts.append(mask_identifier(account.account_id))
    return " · ".join(parts)
