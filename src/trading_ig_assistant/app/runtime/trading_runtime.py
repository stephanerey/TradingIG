"""Thread-safe owner of immutable GUI read models.

This runtime intentionally owns no broker order command. It composes the single
read-only IG session owner used by the legacy path during incremental migration.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from threading import RLock

from trading_ig_assistant.app.projections.account import AccountHeaderVM
from trading_ig_assistant.app.projections.account_projection import (
    build_runtime_health_projection,
    merge_stream_account_metrics,
)
from trading_ig_assistant.app.projections.catalogue import (
    CatalogueVM,
    empty_catalogue_projection,
    mark_stream_rows_stale,
    merge_live_quote,
)
from trading_ig_assistant.app.projections.dashboard import (
    DashboardVM,
    empty_dashboard_projection,
)
from trading_ig_assistant.app.projections.dashboard_projection import (
    merge_account_metrics_into_dashboard,
)
from trading_ig_assistant.app.projections.health import HealthServiceVM
from trading_ig_assistant.app.projections.macro import MacroVM, empty_macro_projection
from trading_ig_assistant.app.projections.optimization import (
    OptimizationReviewVM,
    empty_optimization_review,
)
from trading_ig_assistant.app.projections.paper_history import (
    PaperHistoryVM,
    empty_paper_history_projection,
)
from trading_ig_assistant.app.projections.scanner import ScannerVM
from trading_ig_assistant.app.projections.scanner_projection import (
    build_scanner_projection,
    empty_scanner_projection,
    merge_scanner_analysis,
    merge_scanner_candle_progress,
    merge_scanner_reference_quote,
)
from trading_ig_assistant.app.runtime.ig_session_runtime import (
    ActiveIGConnection,
    AdapterFactory,
    ReadOnlyIGSessionRuntime,
)
from trading_ig_assistant.domain.ai_context import MarketContextSnapshot
from trading_ig_assistant.domain.market_data import AccountMetricsUpdate, Quote
from trading_ig_assistant.services.ig_connection_service import IGConnectionRequest
from trading_ig_assistant.services.market_navigation_catalog_service import (
    IGProductMarketBindingRegistry,
)
from trading_ig_assistant.services.scanner_runtime_batch_service import ScannerRuntimeBatchResult

SnapshotCallback = Callable[[object], None]


class RuntimeSubscription:
    def __init__(self, release: Callable[[], None]) -> None:
        self._release = release
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._release()


class TradingRuntime:
    """Own current read projections and reject stale runtime generations."""

    def __init__(
        self,
        *,
        now_provider: Callable[[], datetime] | None = None,
        ig_adapter_factory: AdapterFactory | None = None,
    ) -> None:
        self._now_provider = now_provider or (lambda: datetime.now(UTC))
        self._generation_id = 0
        self._lock = RLock()
        self._subscribers: dict[str, list[SnapshotCallback]] = {
            "account_header": [],
            "catalogue": [],
            "dashboard": [],
            "health": [],
            "macro": [],
            "optimization": [],
            "paper_history": [],
            "scanner": [],
        }
        self._account_header = self._empty_account_header()
        self._catalogue = self._empty_catalogue()
        self._dashboard = self._empty_dashboard()
        self._health: tuple[HealthServiceVM, ...] = ()
        self._macro = self._empty_macro()
        self._market_context: MarketContextSnapshot | None = None
        self._optimization = self._empty_optimization()
        self._paper_history = self._empty_paper_history()
        self._scanner = self._empty_scanner()
        self._ig_session = ReadOnlyIGSessionRuntime(ig_adapter_factory)

    @property
    def active_ig_connection(self) -> ActiveIGConnection | None:
        return self._ig_session.active_connection

    def connect_ig_read_only(self, request: IGConnectionRequest) -> ActiveIGConnection:
        return self._ig_session.connect(request)

    def switch_ig_account(self, account_id: str) -> ActiveIGConnection:
        return self._ig_session.switch_account(account_id)

    def disconnect_ig(self) -> None:
        self._ig_session.disconnect()

    def replace_ig_connection_for_legacy_migration(
        self,
        connection: ActiveIGConnection | None,
    ) -> None:
        self._ig_session.replace_for_legacy_migration(connection)

    @property
    def generation_id(self) -> int:
        with self._lock:
            return self._generation_id

    def begin_generation(self) -> int:
        with self._lock:
            self._generation_id += 1
            self._account_header = self._empty_account_header()
            self._catalogue = self._empty_catalogue()
            self._dashboard = self._empty_dashboard()
            self._health = ()
            self._macro = self._empty_macro()
            self._market_context = None
            self._optimization = self._empty_optimization()
            self._paper_history = self._empty_paper_history()
            self._scanner = self._empty_scanner()
            generation_id = self._generation_id
        self._notify("account_header", self._account_header)
        self._notify("catalogue", self._catalogue)
        self._notify("dashboard", self._dashboard)
        self._notify("health", self._health)
        self._notify("macro", self._macro)
        self._notify("optimization", self._optimization)
        self._notify("paper_history", self._paper_history)
        self._notify("scanner", self._scanner)
        return generation_id

    def read_account_header(self) -> AccountHeaderVM:
        with self._lock:
            return self._account_header

    def read_health(self) -> tuple[HealthServiceVM, ...]:
        with self._lock:
            return self._health

    def read_dashboard(self) -> DashboardVM:
        with self._lock:
            return self._dashboard

    def read_paper_history(self) -> PaperHistoryVM:
        with self._lock:
            return self._paper_history

    def read_macro(self) -> MacroVM:
        with self._lock:
            return self._macro

    def read_market_context(self) -> MarketContextSnapshot | None:
        """Return the latest immutable advisory context for scanner projection."""

        with self._lock:
            return self._market_context

    def read_optimization(self) -> OptimizationReviewVM:
        with self._lock:
            return self._optimization

    def read_catalogue(self) -> CatalogueVM:
        with self._lock:
            return self._catalogue

    def read_scanner(self) -> ScannerVM:
        with self._lock:
            return self._scanner

    def publish_account_header(self, snapshot: AccountHeaderVM) -> bool:
        with self._lock:
            if snapshot.generation_id != self._generation_id:
                return False
            self._account_header = snapshot
        self._notify("account_header", snapshot)
        return True

    def publish_dashboard(self, snapshot: DashboardVM) -> bool:
        with self._lock:
            if snapshot.generation_id != self._generation_id:
                return False
            self._dashboard = snapshot
        self._notify("dashboard", snapshot)
        return True

    def publish_paper_history(self, snapshot: PaperHistoryVM) -> bool:
        with self._lock:
            if snapshot.generation_id != self._generation_id:
                return False
            self._paper_history = snapshot
        self._notify("paper_history", snapshot)
        return True

    def publish_macro(self, snapshot: MacroVM) -> bool:
        with self._lock:
            if snapshot.generation_id != self._generation_id:
                return False
            self._macro = snapshot
        self._notify("macro", snapshot)
        return True

    def publish_market_context(
        self,
        *,
        generation_id: int,
        snapshot: MarketContextSnapshot | None,
    ) -> bool:
        """Publish advisory context without exposing a broker command surface."""

        with self._lock:
            if generation_id != self._generation_id:
                return False
            self._market_context = snapshot
        return True

    def publish_optimization(self, snapshot: OptimizationReviewVM) -> bool:
        with self._lock:
            if snapshot.generation_id != self._generation_id:
                return False
            self._optimization = snapshot
        self._notify("optimization", snapshot)
        return True

    def publish_catalogue(self, snapshot: CatalogueVM) -> bool:
        with self._lock:
            if snapshot.generation_id != self._generation_id:
                return False
            self._catalogue = snapshot
            scanner = build_scanner_projection(
                generation_id=self._generation_id,
                catalogue=snapshot,
                generated_at_utc=snapshot.generated_at_utc,
                previous=self._scanner,
            )
            self._scanner = scanner
        self._notify("catalogue", snapshot)
        self._notify("scanner", scanner)
        return True

    def publish_live_catalogue_quote(
        self,
        *,
        generation_id: int,
        quote: Quote,
        received_at_utc: datetime,
    ) -> bool:
        with self._lock:
            if generation_id != self._generation_id:
                return False
            snapshot = merge_live_quote(
                self._catalogue,
                quote=quote,
                received_at_utc=received_at_utc,
            )
            if snapshot is None:
                return False
            self._catalogue = snapshot
            scanner = build_scanner_projection(
                generation_id=generation_id,
                catalogue=snapshot,
                generated_at_utc=received_at_utc,
                previous=self._scanner,
            )
            self._scanner = scanner
        self._notify("catalogue", snapshot)
        self._notify("scanner", scanner)
        return True

    def publish_scanner_candle_progress(
        self,
        *,
        generation_id: int,
        reference_epic: str,
        observed_candles: int,
        required_candles: int,
        generated_at_utc: datetime,
    ) -> bool:
        with self._lock:
            if generation_id != self._generation_id:
                return False
            scanner = merge_scanner_candle_progress(
                self._scanner,
                reference_epic=reference_epic,
                observed_candles=observed_candles,
                required_candles=required_candles,
                generated_at_utc=generated_at_utc,
            )
            if scanner is None:
                return True
            self._scanner = scanner
        self._notify("scanner", scanner)
        return True

    def publish_scanner_reference_quote(
        self,
        *,
        generation_id: int,
        quote: Quote,
        received_at_utc: datetime,
    ) -> bool:
        with self._lock:
            if generation_id != self._generation_id:
                return False
            scanner = merge_scanner_reference_quote(
                self._scanner,
                quote=quote,
                received_at_utc=received_at_utc,
            )
            if scanner is None:
                return False
            self._scanner = scanner
        self._notify("scanner", scanner)
        return True

    def publish_scanner_analysis(
        self,
        *,
        generation_id: int,
        result: ScannerRuntimeBatchResult,
        binding_registry: IGProductMarketBindingRegistry,
        generated_at_utc: datetime,
    ) -> bool:
        with self._lock:
            if generation_id != self._generation_id:
                return False
            scanner = merge_scanner_analysis(
                self._scanner,
                result=result,
                binding_registry=binding_registry,
                generated_at_utc=generated_at_utc,
            )
            self._scanner = scanner
        self._notify("scanner", scanner)
        return True

    def publish_account_metrics_update(
        self,
        *,
        generation_id: int,
        update: AccountMetricsUpdate,
        received_at_utc: datetime,
    ) -> bool:
        with self._lock:
            if generation_id != self._generation_id:
                return False
            try:
                header = merge_stream_account_metrics(
                    self._account_header,
                    update,
                    received_at_utc=received_at_utc,
                )
            except ValueError:
                return False
            dashboard = merge_account_metrics_into_dashboard(self._dashboard, header)
            health = _merge_health(
                self._health,
                build_runtime_health_projection(
                    generation_id=generation_id,
                    rest_status=header.ig_rest_status,
                    stream_status="live",
                    ai_status=header.ai_status,
                    observed_at_utc=received_at_utc,
                ),
            )
            self._account_header = header
            self._dashboard = dashboard
            self._health = health
        self._notify("account_header", header)
        self._notify("dashboard", dashboard)
        self._notify("health", health)
        return True

    def publish_ai_status(
        self,
        *,
        generation_id: int,
        status: str,
        observed_at_utc: datetime,
    ) -> bool:
        """Update the header's observed AI lifecycle without changing account data."""

        if status not in {"not_configured", "configured", "running", "ready", "stale"}:
            raise ValueError("unsupported AI runtime status")
        with self._lock:
            if generation_id != self._generation_id:
                return False
            header = replace(
                self._account_header,
                ai_status=status,
                generated_at_utc=observed_at_utc,
            )
            self._account_header = header
        self._notify("account_header", header)
        return True

    def mark_catalogue_stream_stale(
        self,
        *,
        generation_id: int,
        epics: frozenset[str],
        received_at_utc: datetime,
        reason_code: str,
    ) -> bool:
        if not epics:
            return True
        with self._lock:
            if generation_id != self._generation_id:
                return False
            snapshot = mark_stream_rows_stale(
                self._catalogue,
                epics=epics,
                received_at_utc=received_at_utc,
                reason_code=reason_code,
            )
            if snapshot is None:
                return True
            self._catalogue = snapshot
        self._notify("catalogue", snapshot)
        return True

    def publish_stream_status(
        self,
        *,
        generation_id: int,
        status: str,
        observed_at_utc: datetime,
    ) -> bool:
        with self._lock:
            if generation_id != self._generation_id:
                return False
            header = replace(
                self._account_header,
                ig_stream_status=status,
                generated_at_utc=observed_at_utc,
            )
            health = _merge_health(
                self._health,
                build_runtime_health_projection(
                    generation_id=generation_id,
                    rest_status=header.ig_rest_status,
                    stream_status=status,
                    ai_status=header.ai_status,
                    observed_at_utc=observed_at_utc,
                ),
            )
            self._account_header = header
            self._health = health
        self._notify("account_header", header)
        self._notify("health", health)
        return True

    def publish_health(
        self,
        snapshots: tuple[HealthServiceVM, ...],
        *,
        generation_id: int,
    ) -> bool:
        if any(snapshot.generation_id != generation_id for snapshot in snapshots):
            raise ValueError("health snapshots must share the published generation")
        with self._lock:
            if generation_id != self._generation_id:
                return False
            merged = _merge_health(self._health, snapshots)
            self._health = merged
        self._notify("health", merged)
        return True

    def publish_health_service(self, snapshot: HealthServiceVM) -> bool:
        """Upsert one observed service without discarding unrelated health state."""

        with self._lock:
            if snapshot.generation_id != self._generation_id:
                return False
            merged = _merge_health(self._health, (snapshot,))
            self._health = merged
        self._notify("health", merged)
        return True

    def subscribe(self, kind: str, callback: SnapshotCallback) -> RuntimeSubscription:
        with self._lock:
            if kind not in self._subscribers:
                raise ValueError(f"unsupported runtime subscription kind: {kind}")
            self._subscribers[kind].append(callback)

        def release() -> None:
            with self._lock:
                subscribers = self._subscribers[kind]
                if callback in subscribers:
                    subscribers.remove(callback)

        return RuntimeSubscription(release)

    def _notify(self, kind: str, snapshot: object) -> None:
        with self._lock:
            callbacks = tuple(self._subscribers[kind])
        for callback in callbacks:
            callback(snapshot)

    def _empty_account_header(self) -> AccountHeaderVM:
        return AccountHeaderVM(
            generation_id=self._generation_id,
            account_id=None,
            ig_environment=None,
            product_account_type=None,
            execution_mode="ANALYSIS",
            equity=None,
            available_funds=None,
            day_pnl=None,
            week_pnl=None,
            month_pnl=None,
            open_positions_count=None,
            ig_rest_status="disconnected",
            ig_stream_status="disconnected",
            ai_status="not_configured",
            generated_at_utc=self._now_provider(),
        )

    def _empty_dashboard(self) -> DashboardVM:
        return empty_dashboard_projection(self._generation_id, self._now_provider())

    def _empty_catalogue(self) -> CatalogueVM:
        return empty_catalogue_projection(self._generation_id, self._now_provider())

    def _empty_scanner(self) -> ScannerVM:
        return empty_scanner_projection(self._generation_id, self._now_provider())

    def _empty_paper_history(self) -> PaperHistoryVM:
        return empty_paper_history_projection(self._generation_id, self._now_provider())

    def _empty_macro(self) -> MacroVM:
        return empty_macro_projection(self._generation_id, self._now_provider())

    def _empty_optimization(self) -> OptimizationReviewVM:
        return empty_optimization_review(self._generation_id, self._now_provider())


def _merge_health(
    existing: tuple[HealthServiceVM, ...],
    updates: tuple[HealthServiceVM, ...],
) -> tuple[HealthServiceVM, ...]:
    """Keep stable service ordering while replacing only observed service IDs."""

    update_by_id = {snapshot.service_id: snapshot for snapshot in updates}
    merged = tuple(
        update_by_id.pop(snapshot.service_id, snapshot) for snapshot in existing
    )
    return (*merged, *update_by_id.values())
