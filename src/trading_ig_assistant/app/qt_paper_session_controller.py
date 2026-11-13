"""Qt boundary for explicit, local-only Paper session persistence."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

from PyQt5 import QtCore

from trading_ig_assistant.app.projections.common import Availability
from trading_ig_assistant.app.projections.dashboard_projection import (
    build_paper_dashboard_projection,
    merge_account_metrics_into_dashboard,
)
from trading_ig_assistant.app.projections.health import HealthServiceVM
from trading_ig_assistant.app.projections.optimization_projection import (
    build_optimization_review,
)
from trading_ig_assistant.app.projections.paper_history_projection import (
    build_paper_history_projection,
)
from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
from trading_ig_assistant.domain.adapter_contracts import ExecutionStatus
from trading_ig_assistant.domain.market_data import QUOTE_FRESHNESS_SECONDS, Quote
from trading_ig_assistant.persistence.paper_session_codec import (
    decode_paper_session_state,
    encode_paper_session_state,
)
from trading_ig_assistant.persistence.repositories import (
    CorruptPaperSnapshotError,
    PaperSessionSnapshotRepository,
)
from trading_ig_assistant.persistence.sqlite_store import (
    MigrationError,
    SQLiteStore,
    UnsupportedSchemaError,
)
from trading_ig_assistant.services.paper_session import (
    PaperSessionService,
    PaperTicketSubmission,
)

LOGGER = logging.getLogger(__name__)

_PERSISTENCE_ERRORS = (
    CorruptPaperSnapshotError,
    MigrationError,
    OSError,
    RuntimeError,
    sqlite3.DatabaseError,
    UnsupportedSchemaError,
    ValueError,
)


class PaperSessionController(QtCore.QObject):
    """Own one local Paper session without exposing any IG execution command."""

    message = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    restore_confirmation_required = QtCore.pyqtSignal()
    close_confirmation_required = QtCore.pyqtSignal(str)
    submission_completed = QtCore.pyqtSignal(object)
    state_changed = QtCore.pyqtSignal(bool)

    def __init__(
        self,
        *,
        runtime: TradingRuntime,
        database_path: Path,
        session: PaperSessionService | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__()
        self._runtime = runtime
        self._database_path = Path(database_path)
        self._session = session or PaperSessionService()
        self._now_provider = now_provider or (lambda: datetime.now(UTC))
        self._pending_restore: PaperSessionService | None = None
        self._last_checkpoint_at: datetime | None = None
        self._last_error_at: datetime | None = None
        self._projection_timer = QtCore.QTimer(self)
        self._projection_timer.setSingleShot(True)
        self._projection_timer.setInterval(250)
        self._projection_timer.timeout.connect(self.publish_projection)
        self.publish_projection()

    @property
    def session(self) -> PaperSessionService:
        return self._session

    @QtCore.pyqtSlot()
    def publish_projection(self) -> None:
        """Publish current Paper state for the runtime's active generation."""

        now = self._now_provider()
        dashboard = build_paper_dashboard_projection(
            generation_id=self._runtime.generation_id,
            positions=self._session.position_snapshots(),
            events=self._session.events(),
            generated_at_utc=now,
        )
        dashboard = merge_account_metrics_into_dashboard(
            dashboard,
            self._runtime.read_account_header(),
        )
        self._runtime.publish_dashboard(dashboard)
        self._runtime.publish_paper_history(
            build_paper_history_projection(
                generation_id=self._runtime.generation_id,
                events=self._session.events(),
                generated_at_utc=now,
            )
        )
        self._runtime.publish_optimization(
            build_optimization_review(
                generation_id=self._runtime.generation_id,
                events=self._session.events(),
                generated_at_utc=now,
            )
        )
        self._publish_health()
        self.state_changed.emit(self._session.has_state())

    @QtCore.pyqtSlot()
    def save(self) -> None:
        """Persist one explicit append-only checkpoint of local Paper state."""

        if not self._session.has_state():
            self.error.emit("paper.save_empty")
            return
        saved_at = self._now_provider()
        snapshot_id = f"paper-snapshot-{uuid4().hex}"
        try:
            repository = self._repository()
            repository.save(
                snapshot_id=snapshot_id,
                session_id=self._session.session_id,
                saved_at_utc=saved_at,
                payload=encode_paper_session_state(self._session.checkpoint_state()),
            )
        except _PERSISTENCE_ERRORS as exc:
            LOGGER.error("Explicit GUI V2 Paper save failed: %s", exc)
            self._last_error_at = self._now_provider()
            self._publish_health()
            self.error.emit(f"paper.save_failed|{exc}")
            return
        self._last_checkpoint_at = saved_at
        self._last_error_at = None
        self._publish_health()
        self.message.emit("paper.save_succeeded")

    @QtCore.pyqtSlot(object)
    def submit(self, value: object) -> None:
        """Submit one explicitly confirmed immutable request to the local Paper session."""

        if not isinstance(value, PaperTicketSubmission):
            self.error.emit("paper.open_invalid")
            return
        now = self._now_provider()
        quote_age = (now - value.quote.observed_at_utc).total_seconds()
        if not 0 <= quote_age <= QUOTE_FRESHNESS_SECONDS:
            self.error.emit("paper.open_stale")
            return
        if value.ticket.intent.expires_at_utc <= now:
            self.error.emit("paper.open_expired")
            return
        try:
            record = self._session.submit(value)
        except ValueError as exc:
            self.error.emit(f"paper.open_failed|{exc}")
            return
        self.publish_projection()
        self.submission_completed.emit(record)
        if record.outcome.execution_result.status is ExecutionStatus.CONFIRMED:
            self.message.emit("paper.open_succeeded")
        else:
            detail = (
                record.outcome.execution_result.message
                or record.outcome.execution_result.status.value
            )
            self.error.emit(
                f"paper.open_failed|{detail}"
            )

    @QtCore.pyqtSlot(object)
    def process_market_quote(self, value: object) -> None:
        """Apply an observed quote only to products already tracked by local Paper."""

        if not isinstance(value, Quote) or not self._session.tracks_product(value.epic):
            return
        results = self._session.process_market_quote(
            value,
            observed_at_utc=self._now_provider(),
        )
        if results:
            self._projection_timer.stop()
            self.publish_projection()
        elif not self._projection_timer.isActive():
            self._projection_timer.start()

    @QtCore.pyqtSlot()
    def invalidate_market_quotes(self) -> None:
        """Mark local Paper valuations stale when their read-only source disconnects."""

        self._projection_timer.stop()
        self._session.invalidate_market_quotes()
        self.publish_projection()

    @QtCore.pyqtSlot(str, str)
    def move_stop(self, position_id: str, stop_text: str) -> None:
        try:
            stop = Decimal(stop_text.strip().replace(",", "."))
        except (InvalidOperation, ValueError):
            self.error.emit("paper.stop_invalid")
            return
        try:
            result = self._session.move_stop(position_id, stop)
        except (KeyError, ValueError) as exc:
            self.error.emit(f"paper.stop_failed|{exc}")
            return
        self.publish_projection()
        if result.status is ExecutionStatus.CONFIRMED:
            self.message.emit("paper.stop_succeeded")
        else:
            self.error.emit(f"paper.stop_failed|{result.message or result.status.value}")

    @QtCore.pyqtSlot(str)
    def request_close(self, position_id: str) -> None:
        if position_id.strip():
            self.close_confirmation_required.emit(position_id)

    @QtCore.pyqtSlot(str, bool)
    def confirm_close(self, position_id: str, confirmed: bool) -> None:
        if not confirmed:
            return
        try:
            result = self._session.close_position(position_id)
        except (KeyError, ValueError) as exc:
            self.error.emit(f"paper.close_failed|{exc}")
            return
        self.publish_projection()
        if result.status is ExecutionStatus.CONFIRMED:
            self.message.emit("paper.close_succeeded")
        else:
            self.error.emit(f"paper.close_failed|{result.message or result.status.value}")

    @QtCore.pyqtSlot()
    def request_restore(self) -> None:
        """Validate the latest checkpoint, then request confirmation if destructive."""

        self._pending_restore = None
        if not self._database_path.exists():
            self.error.emit("paper.restore_missing")
            return
        try:
            snapshot = self._repository().latest()
            if snapshot is None:
                self.error.emit("paper.restore_empty")
                return
            restored = PaperSessionService.from_checkpoint_state(
                decode_paper_session_state(snapshot.payload)
            )
            restored.record_restore(snapshot.snapshot_id)
        except _PERSISTENCE_ERRORS as exc:
            LOGGER.error("Explicit GUI V2 Paper restore failed: %s", exc)
            self._last_error_at = self._now_provider()
            self._publish_health()
            self.error.emit(f"paper.restore_failed|{exc}")
            return
        self._pending_restore = restored
        if self._session.has_state():
            self.restore_confirmation_required.emit()
            return
        self.confirm_restore(True)

    @QtCore.pyqtSlot(bool)
    def confirm_restore(self, confirmed: bool) -> None:
        """Apply a previously validated checkpoint after explicit confirmation."""

        restored = self._pending_restore
        self._pending_restore = None
        if not confirmed or restored is None:
            return
        self._session = restored
        self._last_checkpoint_at = self._now_provider()
        self._last_error_at = None
        self.publish_projection()
        self.message.emit("paper.restore_succeeded")

    def _repository(self) -> PaperSessionSnapshotRepository:
        store = SQLiteStore(self._database_path)
        store.initialize()
        return PaperSessionSnapshotRepository(store)

    def _publish_health(self) -> None:
        now = self._now_provider()
        if self._last_error_at is not None:
            status = Availability.UNAVAILABLE
            summary = "error"
            reasons = ("PAPER_PERSISTENCE_ERROR",)
        elif self._session.has_state() and self._last_checkpoint_at is None:
            status = Availability.WARMING_UP
            summary = "unsaved changes"
            reasons = ("PAPER_SESSION_DIRTY",)
        elif self._last_checkpoint_at is not None:
            status = Availability.READY
            summary = "snapshot saved"
            reasons = ("PAPER_SNAPSHOT_AVAILABLE",)
        else:
            status = Availability.READY
            summary = "empty session"
            reasons = ("PAPER_SESSION_EMPTY",)
        self._runtime.publish_health_service(
            HealthServiceVM(
                generation_id=self._runtime.generation_id,
                service_id="paper-sqlite",
                status=status,
                summary=summary,
                observed_at_utc=now,
                last_success_at_utc=self._last_checkpoint_at,
                last_error_at_utc=self._last_error_at,
                reason_codes=reasons,
            )
        )
