"""Qt worker controller for explicit bounded IG catalogue searches."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from PyQt5 import QtCore

from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.app.projections.catalogue import (
    ProductRowVM,
    build_catalogue_projection,
    merge_catalogue_product_details,
    merge_catalogue_snapshots,
)
from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
from trading_ig_assistant.domain.instruments import MarketSummary
from trading_ig_assistant.services.product_discovery_service import (
    ProductDiscoveryService,
    read_discovery_report,
)


class _CatalogueSearchWorker(QtCore.QObject):
    succeeded = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, runtime: TradingRuntime, query: str) -> None:
        super().__init__()
        self._runtime = runtime
        self._query = query

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            connection = self._runtime.active_ig_connection
            if connection is None:
                raise RuntimeError("catalogue.not_connected")
            generation_id = self._runtime.generation_id
            result = ProductDiscoveryService(connection.adapter).search_product_summaries(
                self._query
            )
            snapshot = build_catalogue_projection(
                generation_id=generation_id,
                query=self._query,
                products=tuple(result.products),
                generated_at_utc=datetime.now(UTC),
                error_count=len(result.errors),
            )
            current = self._runtime.read_catalogue()
            if current.rows:
                snapshot = merge_catalogue_snapshots(current, snapshot)
            if not self._runtime.publish_catalogue(snapshot):
                raise RuntimeError("catalogue.context_changed")
            self.succeeded.emit(snapshot)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class _CatalogueDetailsWorker(QtCore.QObject):
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, runtime: TradingRuntime, row: ProductRowVM) -> None:
        super().__init__()
        self._runtime = runtime
        self._row = row

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            connection = self._runtime.active_ig_connection
            if connection is None:
                raise RuntimeError("catalogue.not_connected")
            generation_id = self._runtime.generation_id
            service = ProductDiscoveryService(connection.adapter)
            details = connection.adapter.get_market_details(self._row.epic)
            product = service.classify_product(
                MarketSummary(
                    epic=self._row.epic,
                    instrument_name=self._row.name,
                    market_status=self._row.status,
                ),
                details,
            )
            current = self._runtime.read_catalogue()
            snapshot = merge_catalogue_product_details(current, product=product)
            if snapshot is None:
                raise RuntimeError("catalogue.product_changed")
            if generation_id != self._runtime.generation_id or not self._runtime.publish_catalogue(
                snapshot
            ):
                raise RuntimeError("catalogue.context_changed")
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class CatalogueSearchController(QtCore.QObject):
    busy_changed = QtCore.pyqtSignal(bool)
    details_busy_changed = QtCore.pyqtSignal(bool)
    error = QtCore.pyqtSignal(str)

    def __init__(
        self,
        runtime: TradingRuntime,
        *,
        cache_path_provider: Callable[[IGEnvironment], Path] | None = None,
    ) -> None:
        super().__init__()
        self._runtime = runtime
        self._cache_path_provider = cache_path_provider or default_discovery_cache_path
        self._thread: QtCore.QThread | None = None
        self._worker: _CatalogueSearchWorker | None = None
        self._details_thread: QtCore.QThread | None = None
        self._details_worker: _CatalogueDetailsWorker | None = None

    @property
    def busy(self) -> bool:
        return self._thread is not None

    @property
    def details_busy(self) -> bool:
        return self._details_thread is not None

    @QtCore.pyqtSlot(str)
    def search(self, query: str) -> None:
        normalized = query.strip()
        if self.busy:
            self.error.emit("catalogue.busy")
            return
        if self._runtime.active_ig_connection is None:
            self.error.emit("catalogue.not_connected")
            return
        if not 3 <= len(normalized) <= 100:
            self.error.emit("catalogue.invalid_query")
            return
        thread = QtCore.QThread(self)
        worker = _CatalogueSearchWorker(self._runtime, normalized)
        self._thread, self._worker = thread, worker
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.failed.connect(self.error)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_worker)
        self.busy_changed.emit(True)
        thread.start()

    @QtCore.pyqtSlot(object)
    def resolve_product_details(self, value: object) -> None:
        """Fetch one explicitly selected product's read-only metadata, never a bulk crawl."""

        if not isinstance(value, ProductRowVM):
            return
        if self.details_busy:
            self.error.emit("catalogue.details_busy")
            return
        if self._runtime.active_ig_connection is None:
            self.error.emit("catalogue.not_connected")
            return
        thread = QtCore.QThread(self)
        worker = _CatalogueDetailsWorker(self._runtime, value)
        self._details_thread, self._details_worker = thread, worker
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.failed.connect(self.error)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_details_worker)
        self.details_busy_changed.emit(True)
        thread.start()

    def load_cached_inventory(self, environment: IGEnvironment) -> bool:
        path = self._cache_path_provider(environment)
        try:
            results = read_discovery_report(path)
        except (OSError, ValueError):
            self.error.emit("catalogue.cache_invalid")
            return False
        by_epic = {
            product.epic: product
            for result in results
            for product in result.products
            if product.epic
        }
        if not by_epic:
            return False
        snapshot = build_catalogue_projection(
            generation_id=self._runtime.generation_id,
            query=None,
            products=tuple(by_epic.values()),
            generated_at_utc=datetime.fromtimestamp(path.stat().st_mtime, tz=UTC),
            error_count=sum(len(result.errors) for result in results),
            kind="inventory",
            source="local-discovery-cache",
        )
        return self._runtime.publish_catalogue(snapshot)

    @QtCore.pyqtSlot()
    def _clear_worker(self) -> None:
        self._thread = None
        self._worker = None
        self.busy_changed.emit(False)

    @QtCore.pyqtSlot()
    def _clear_details_worker(self) -> None:
        self._details_thread = None
        self._details_worker = None
        self.details_busy_changed.emit(False)


def default_discovery_cache_path(environment: IGEnvironment) -> Path:
    return Path.home() / ".trading_ig_assistant" / f"product_discovery_{environment.value}.json"
