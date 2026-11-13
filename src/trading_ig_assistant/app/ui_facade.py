"""Read-only application facade consumed by GUI V2 pages."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from trading_ig_assistant.app.projections.account import AccountHeaderVM
from trading_ig_assistant.app.projections.catalogue import CatalogueVM
from trading_ig_assistant.app.projections.dashboard import DashboardVM
from trading_ig_assistant.app.projections.health import HealthServiceVM
from trading_ig_assistant.app.projections.macro import MacroVM
from trading_ig_assistant.app.projections.optimization import OptimizationReviewVM
from trading_ig_assistant.app.projections.paper_history import PaperHistoryVM
from trading_ig_assistant.app.projections.scanner import ScannerVM
from trading_ig_assistant.app.runtime.trading_runtime import RuntimeSubscription, TradingRuntime


class TradingUIFacade(Protocol):
    def read_account_header(self) -> AccountHeaderVM: ...

    def read_health(self) -> tuple[HealthServiceVM, ...]: ...

    def read_dashboard(self) -> DashboardVM: ...

    def read_catalogue(self) -> CatalogueVM: ...

    def read_scanner(self) -> ScannerVM: ...

    def read_paper_history(self) -> PaperHistoryVM: ...

    def read_macro(self) -> MacroVM: ...

    def read_optimization(self) -> OptimizationReviewVM: ...

    def subscribe(self, kind: str, callback: Callable[[object], None]) -> RuntimeSubscription: ...


class RuntimeUIFacade:
    """Expose runtime read models only; no broker or Paper command exists here."""

    def __init__(self, runtime: TradingRuntime) -> None:
        self._runtime = runtime

    def read_account_header(self) -> AccountHeaderVM:
        return self._runtime.read_account_header()

    def read_health(self) -> tuple[HealthServiceVM, ...]:
        return self._runtime.read_health()

    def read_dashboard(self) -> DashboardVM:
        return self._runtime.read_dashboard()

    def read_catalogue(self) -> CatalogueVM:
        return self._runtime.read_catalogue()

    def read_scanner(self) -> ScannerVM:
        return self._runtime.read_scanner()

    def read_paper_history(self) -> PaperHistoryVM:
        return self._runtime.read_paper_history()

    def read_macro(self) -> MacroVM:
        return self._runtime.read_macro()

    def read_optimization(self) -> OptimizationReviewVM:
        return self._runtime.read_optimization()

    def subscribe(
        self,
        kind: str,
        callback: Callable[[object], None],
    ) -> RuntimeSubscription:
        return self._runtime.subscribe(kind, callback)


def build_empty_ui_facade() -> RuntimeUIFacade:
    return RuntimeUIFacade(TradingRuntime())
