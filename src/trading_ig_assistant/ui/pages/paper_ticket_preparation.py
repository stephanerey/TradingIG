"""Bilingual, read-only Paper ticket preparation checkpoint."""

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.app.projections.common import Availability
from trading_ig_assistant.app.projections.paper_ticket import PaperTicketPreparationVM
from trading_ig_assistant.domain.market_data import Quote
from trading_ig_assistant.domain.products import (
    AssetClass,
    ProductDirection,
    ProductType,
    TradableProduct,
)
from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
from trading_ig_assistant.ui.ticket_view import PaperTicketWidget


class PaperTicketPreparationWidget(QtWidgets.QWidget):
    paper_submission_requested = QtCore.pyqtSignal(object)

    def __init__(self, language: LanguageManager) -> None:
        super().__init__()
        self._language = language
        self._snapshot: PaperTicketPreparationVM | None = None
        self._draft_product_key: tuple[object, ...] | None = None
        layout = QtWidgets.QVBoxLayout(self)
        self.safety = QtWidgets.QLabel()
        self.safety.setWordWrap(True)
        layout.addWidget(self.safety)
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        actions = QtWidgets.QHBoxLayout()
        self.prepare_button = QtWidgets.QPushButton()
        self.prepare_button.setEnabled(False)
        self.prepare_button.clicked.connect(self._open_draft)
        actions.addWidget(self.prepare_button)
        self.back_button = QtWidgets.QPushButton()
        self.back_button.setVisible(False)
        self.back_button.clicked.connect(self._close_draft)
        actions.addWidget(self.back_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, stretch=1)
        self.draft = PaperTicketWidget(allow_execution=True)
        self.draft.paper_execution_requested.connect(self.paper_submission_requested)
        self.draft.setVisible(False)
        layout.addWidget(self.draft, stretch=1)
        self.retranslate_ui()

    def set_snapshot(self, snapshot: PaperTicketPreparationVM) -> None:
        previous_epic = self._snapshot.product_epic if self._snapshot is not None else None
        self._snapshot = snapshot
        if previous_epic is not None and previous_epic != snapshot.product_epic:
            self._close_draft()
        if snapshot.availability is Availability.READY:
            self._configure_draft(snapshot)
        else:
            self._close_draft()
            self._draft_product_key = None
            self.draft.set_product(None)
        self._refresh()

    def retranslate_ui(self) -> None:
        self.safety.setText(self._language.text("paper.ticket.preparation_safety"))
        self.prepare_button.setText(self._language.text("paper.ticket.prepare_draft"))
        self.back_button.setText(self._language.text("paper.ticket.back_to_evidence"))
        self.table.setHorizontalHeaderLabels(
            (
                self._language.text("paper.ticket.field"),
                self._language.text("paper.ticket.value"),
            )
        )
        self._refresh()

    def _refresh(self) -> None:
        snapshot = self._snapshot
        if snapshot is None:
            self.status.setText(self._language.text("paper.ticket.select_product"))
            self.table.setRowCount(0)
            self.prepare_button.setEnabled(False)
            return
        if snapshot.availability is Availability.READY:
            self.status.setText(self._language.text("paper.ticket.ready"))
        else:
            self.status.setText(
                self._language.text("paper.ticket.blocked").format(
                    status=snapshot.availability.value.upper()
                )
            )
        self.prepare_button.setEnabled(snapshot.availability is Availability.READY)
        rows = [
            (self._language.text("paper.ticket.product"), snapshot.product_name),
            (self._language.text("paper.ticket.product_epic"), snapshot.product_epic),
            (self._language.text("paper.ticket.product_type"), snapshot.product_type.upper()),
            (
                self._language.text("paper.ticket.underlying"),
                snapshot.canonical_underlying_id or "N/A",
            ),
            (
                self._language.text("paper.ticket.reference_epic"),
                snapshot.reference_epic or "N/A",
            ),
            (
                self._language.text("paper.ticket.binding_provenance"),
                ", ".join(snapshot.binding_provenance) or "N/A",
            ),
            (
                self._language.text("paper.ticket.metadata_source"),
                snapshot.metadata_source or "N/A",
            ),
            (self._language.text("paper.ticket.currency"), snapshot.currency or "N/A"),
            (
                self._language.text("paper.ticket.deal_constraints"),
                self._deal_constraints(snapshot),
            ),
            (
                self._language.text("paper.ticket.bid_offer"),
                f"{snapshot.bid if snapshot.bid is not None else 'N/A'} / "
                f"{snapshot.offer if snapshot.offer is not None else 'N/A'}",
            ),
            (
                self._language.text("paper.ticket.market_status"),
                snapshot.market_status or "N/A",
            ),
            (
                self._language.text("paper.ticket.quote_source"),
                f"{snapshot.quote_source} · "
                f"{snapshot.quote_received_at_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            ),
        ]
        rows.extend(
            (
                self._language.text("paper.ticket.blocker"),
                self._language.text(f"paper.ticket.reason.{reason}"),
            )
            for reason in snapshot.reason_codes
        )
        self.table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for column, value in enumerate(values):
                self.table.setItem(row, column, QtWidgets.QTableWidgetItem(value))

    def _configure_draft(self, snapshot: PaperTicketPreparationVM) -> None:
        try:
            product_type = ProductType(snapshot.product_type)
        except ValueError:
            product_type = ProductType.UNKNOWN
        try:
            direction = ProductDirection(snapshot.product_direction)
        except ValueError:
            direction = ProductDirection.UNKNOWN
        try:
            asset_class = AssetClass(snapshot.asset_class)
        except ValueError:
            asset_class = AssetClass.OTHER
        product_key = (
            snapshot.product_epic,
            snapshot.product_name,
            product_type,
            direction,
            asset_class,
            snapshot.currency,
            snapshot.min_size,
            snapshot.max_size,
            snapshot.lot_size,
            snapshot.ko_level,
            snapshot.strike,
        )
        if product_key != self._draft_product_key:
            self.draft.set_product(
                TradableProduct(
                    epic=snapshot.product_epic,
                    name=snapshot.product_name,
                    product_type=product_type,
                    direction=direction,
                    currency=snapshot.currency,
                    min_size=(
                        float(snapshot.min_size) if snapshot.min_size is not None else None
                    ),
                    max_size=(
                        float(snapshot.max_size) if snapshot.max_size is not None else None
                    ),
                    lot_size=(
                        float(snapshot.lot_size) if snapshot.lot_size is not None else None
                    ),
                    status=snapshot.market_status,
                    ko_level=(
                        float(snapshot.ko_level) if snapshot.ko_level is not None else None
                    ),
                    strike=(float(snapshot.strike) if snapshot.strike is not None else None),
                    asset_class=asset_class,
                    bid=float(snapshot.bid) if snapshot.bid is not None else None,
                    offer=float(snapshot.offer) if snapshot.offer is not None else None,
                )
            )
            self.draft.set_verified_underlying_id(snapshot.canonical_underlying_id)
            self._draft_product_key = product_key
        self.draft.set_quote(
            Quote(
                epic=snapshot.product_epic,
                bid=float(snapshot.bid) if snapshot.bid is not None else None,
                offer=float(snapshot.offer) if snapshot.offer is not None else None,
                market_state=snapshot.market_status,
                raw={"DELAY": "0"},
            ),
            received_at_utc=snapshot.quote_received_at_utc,
        )

    def _open_draft(self) -> None:
        snapshot = self._snapshot
        if snapshot is None or snapshot.availability is not Availability.READY:
            return
        self.table.setVisible(False)
        self.prepare_button.setVisible(False)
        self.back_button.setVisible(True)
        self.draft.setVisible(True)

    def _close_draft(self) -> None:
        self.draft.setVisible(False)
        self.back_button.setVisible(False)
        self.table.setVisible(True)
        self.prepare_button.setVisible(True)

    def show_submission_result(self, record: object) -> None:
        from trading_ig_assistant.services.paper_session import PaperOrderRecord

        if isinstance(record, PaperOrderRecord):
            self.draft.show_execution_result(record)

    def show_submission_cancelled(self) -> None:
        self.draft.show_execution_cancelled()

    @staticmethod
    def _deal_constraints(snapshot: PaperTicketPreparationVM) -> str:
        values = (
            f"min={snapshot.min_size if snapshot.min_size is not None else 'N/A'}",
            f"max={snapshot.max_size if snapshot.max_size is not None else 'N/A'}",
            f"lot={snapshot.lot_size if snapshot.lot_size is not None else 'N/A'}",
            f"KO={snapshot.ko_level if snapshot.ko_level is not None else 'N/A'}",
            f"strike={snapshot.strike if snapshot.strike is not None else 'N/A'}",
        )
        return " · ".join(values)
