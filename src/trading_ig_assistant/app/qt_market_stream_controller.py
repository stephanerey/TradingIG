"""Qt controller for a bounded, read-only GUI V2 catalogue quote scope."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from PyQt5 import QtCore

from trading_ig_assistant.adapters.ig_rest import IGSession
from trading_ig_assistant.adapters.ig_streaming import IGStreamingAdapter, StreamingEventSink
from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
from trading_ig_assistant.app.streaming_bridge import StreamingEventBridge
from trading_ig_assistant.domain.market_data import (
    AccountMetricsUpdate,
    ChartCandleUpdate,
    Quote,
)


class MarketStreamAdapter(Protocol):
    def start(self) -> None: ...

    def subscribe_markets(self, epics: list[str]) -> None: ...

    def subscribe_markets_individually(self, epics: list[str]) -> None: ...

    def subscribe_account(self) -> None: ...

    def subscribe_charts(self, epics: list[str], scale: str = "1MINUTE") -> None: ...

    def subscribe_charts_individually(
        self, epics: list[str], scale: str = "1MINUTE"
    ) -> None: ...

    def stop(self) -> None: ...


StreamAdapterFactory = Callable[
    [IGSession, str, StreamingEventSink],
    MarketStreamAdapter,
]


def _default_adapter_factory(
    session: IGSession,
    account_id: str,
    event_sink: StreamingEventSink,
) -> MarketStreamAdapter:
    return IGStreamingAdapter(
        session=session,
        account_id=account_id,
        event_sink=event_sink,
    )


# IG's default cap is shared: reserve one item for ACCOUNT metrics.
CATALOGUE_STREAM_ITEM_BUDGET = 39
DEFAULT_PRIORITY_REFERENCE_EPICS = (
    "IX.D.NASDAQ.IFD.IP",  # US Tech 100
    "IX.D.CAC.IMF.IP",  # France 40
    "IX.D.DAX.IFMM.IP",  # Germany 40
    "CS.D.CFEGOLD.CEF.IP",  # Spot Gold
    "CC.D.CL.UEF.IP",  # US Crude
    "IX.D.SPTRD.IFE.IP",  # US 500
    "IX.D.DOW.IFE.IP",  # Wall Street
    "IX.D.FTSE.IFE.IP",  # FTSE 100
    "CS.D.EURUSD.CEF.IP",  # EUR/USD
    "CS.D.GBPUSD.CFD.IP",  # GBP/USD
)


class CatalogueMarketStreamController(QtCore.QObject):
    """Own one ACCOUNT item and a bounded PRICE subscription on one connection."""

    coverage_changed = QtCore.pyqtSignal(str, int, int, int)
    chart_update_received = QtCore.pyqtSignal(object)
    chart_market_unavailable = QtCore.pyqtSignal(str)
    quote_received = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(str)

    def __init__(
        self,
        runtime: TradingRuntime,
        *,
        adapter_factory: StreamAdapterFactory = _default_adapter_factory,
        now_provider: Callable[[], datetime] | None = None,
        item_budget: int = CATALOGUE_STREAM_ITEM_BUDGET,
        priority_epics: tuple[str, ...] = DEFAULT_PRIORITY_REFERENCE_EPICS,
        chart_epics: tuple[str, ...] = (),
    ) -> None:
        super().__init__()
        self._runtime = runtime
        self._adapter_factory = adapter_factory
        self._now_provider = now_provider or (lambda: datetime.now(UTC))
        self._adapter: MarketStreamAdapter | None = None
        self._bridge: StreamingEventBridge | None = None
        self._generation_id: int | None = None
        self._epics: tuple[str, ...] = ()
        self._catalogue_total = 0
        self._state = "disconnected"
        self._chart_epics = tuple(dict.fromkeys(epic for epic in chart_epics if epic))
        price_capacity = CATALOGUE_STREAM_ITEM_BUDGET - len(self._chart_epics)
        if price_capacity < 0:
            raise ValueError("chart stream scope exceeds the bounded IG item budget")
        self._item_budget = max(0, min(item_budget, price_capacity))
        self._priority_epics = tuple(dict.fromkeys(epic for epic in priority_epics if epic))
        self._requested_epics: tuple[str, ...] = ()
        self._requested_total = 0
        self._protected_epics: tuple[str, ...] = ()
        self._tracked_epics: tuple[str, ...] = ()
        self._active_priority_count = 0
        self._chart_permission_fallback_attempted = False
        self._chart_permission_fallback_active = False
        self._chart_degraded_notice_emitted = False
        self._unavailable_chart_epics: set[str] = set()
        self._price_group_fallback_attempted = False
        self._price_group_fallback_active = False
        self._price_degraded_notice_emitted = False
        self._unavailable_price_epics: set[str] = set()
        # The REST worker publishes the active session before its success signal reaches
        # the GUI thread.  Do not let catalogue notifications start Lightstreamer in that
        # short, unconfirmed window.  Tests and legacy migration paths that construct the
        # controller around an already-active session remain ready by default.
        self._connection_ready = runtime.active_ig_connection is not None

    @property
    def subscribed_epics(self) -> tuple[str, ...]:
        return self._epics

    def sync_inventory(self, snapshot: object) -> None:
        from trading_ig_assistant.app.projections.catalogue import CatalogueVM

        if not isinstance(snapshot, CatalogueVM):
            return
        available = tuple(row.epic for row in snapshot.rows if row.epic)
        self._catalogue_total = len(available)
        # Inventory availability and the live PRICE scope are distinct concerns.  The
        # scanner explicitly requests its visible rows; when it is hidden only followed
        # products, open simulations and configured priorities must stay subscribed.
        available_set = frozenset(available)
        self._requested_epics = tuple(
            epic for epic in self._requested_epics if epic in available_set
        )
        self._apply_scope()

    @QtCore.pyqtSlot(bool)
    def set_connection_ready(self, ready: bool) -> None:
        """Authorize streaming only after the GUI confirms the REST connection context."""

        normalized = bool(ready)
        if normalized == self._connection_ready:
            if normalized:
                self._apply_scope()
            return
        self._connection_ready = normalized
        if not normalized:
            self.stop()
            return
        self._apply_scope()

    @QtCore.pyqtSlot(object, int)
    def sync_scope(self, epics: object, total_count: int) -> None:
        self._requested_epics = tuple(
            dict.fromkeys(str(epic).strip() for epic in epics if str(epic).strip())
        )
        self._requested_total = max(0, total_count)
        self._apply_scope()

    @QtCore.pyqtSlot(object)
    def protect_epics(self, epics: object) -> None:
        """Reserve PRICE capacity for products with open local Paper positions."""

        self._protected_epics = tuple(
            dict.fromkeys(str(epic).strip() for epic in epics if str(epic).strip())
        )
        self._apply_scope()

    @QtCore.pyqtSlot(object)
    def track_epics(self, epics: object) -> None:
        """Prioritize exact catalogue products explicitly followed by the operator."""

        self._tracked_epics = tuple(
            dict.fromkeys(str(epic).strip() for epic in epics if str(epic).strip())
        )
        self._apply_scope()

    def _apply_scope(self) -> None:
        requested = self._requested_epics
        known_epics = {row.epic for row in self._runtime.read_catalogue().rows}
        priorities = tuple(epic for epic in self._priority_epics if epic in known_epics)
        price_priorities = tuple(
            epic
            for epic in priorities
            if epic not in self._chart_epics and epic not in self._unavailable_price_epics
        )
        protected = tuple(
            epic
            for epic in self._protected_epics
            if epic in known_epics
            and epic not in self._chart_epics
            and epic not in self._unavailable_price_epics
        )
        tracked = tuple(
            epic
            for epic in self._tracked_epics
            if epic in known_epics and epic not in self._unavailable_price_epics
        )
        normalized = tuple(
            dict.fromkeys(
                (
                    *protected,
                    *tracked,
                    *price_priorities,
                    *(
                        epic
                        for epic in requested
                        if epic in known_epics
                        and epic not in self._chart_epics
                        and epic not in self._unavailable_price_epics
                    ),
                )
            )
        )[: self._item_budget]
        priority_scope = frozenset((*price_priorities, *protected, *tracked))
        self._active_priority_count = (
            len(self._chart_epics) - len(self._unavailable_chart_epics)
        ) + sum(
            epic in priority_scope for epic in normalized
        )
        self._catalogue_total = self._requested_total
        if not self._connection_ready:
            self.coverage_changed.emit(
                "disconnected",
                0,
                self._catalogue_total,
                0,
            )
            return
        connection = self._runtime.active_ig_connection
        if connection is None or not connection.current_account_id:
            if self._adapter is not None:
                self.stop()
            else:
                self.coverage_changed.emit(
                    "disconnected",
                    0,
                    self._catalogue_total,
                    0,
                )
            return
        if not normalized and not self._chart_epics:
            self.stop()
            return
        session = getattr(connection.adapter, "session", None)
        if session is None or not session.lightstreamer_endpoint:
            self.error.emit("stream.unavailable")
            self.coverage_changed.emit("failed", 0, self._catalogue_total, 0)
            return
        if self._adapter is not None and normalized == self._epics:
            self.coverage_changed.emit(
                self._state,
                self._coverage_count,
                self._catalogue_total,
                self._active_priority_count,
            )
            return
        generation_id = self._runtime.generation_id
        if self._adapter is None or self._generation_id != generation_id:
            self.stop()
            bridge = StreamingEventBridge(generation_id)
            bridge.quote_received.connect(self._on_quote)
            bridge.account_metrics_received.connect(self._on_account_metrics)
            bridge.chart_received.connect(self._on_chart)
            bridge.status_changed.connect(self._on_status)
            bridge.error_received.connect(self._on_error)
            self._adapter = self._adapter_factory(
                session,
                connection.current_account_id,
                bridge,
            )
            self._generation_id = generation_id
            self._bridge = bridge
            try:
                self._adapter.start()
            except Exception as exc:
                self.stop()
                self.error.emit(str(exc))
                return
        previous_epics = self._epics
        removed = frozenset(previous_epics) - frozenset(normalized)
        # Commit the new scope before publishing stale catalogue rows.  That publication is
        # synchronous on the GUI thread and calls sync_inventory(), which may re-enter this
        # method.  Keeping the previous scope until after the publication caused the same rows
        # to be marked stale recursively until Python's recursion limit was reached.
        self._epics = normalized
        if removed:
            self._runtime.mark_catalogue_stream_stale(
                generation_id=generation_id,
                epics=removed,
                received_at_utc=self._now_provider(),
                reason_code="STREAM_SCOPE_RELEASED",
            )
        self._publish_status("connecting")
        try:
            if self._adapter is not None:
                self._adapter.subscribe_account()
                if self._chart_epics:
                    if self._chart_permission_fallback_active:
                        self._adapter.subscribe_charts_individually(
                            list(self._chart_epics), "1MINUTE"
                        )
                    else:
                        self._adapter.subscribe_charts(list(self._chart_epics), "1MINUTE")
                if normalized:
                    if self._price_group_fallback_active:
                        self._adapter.subscribe_markets_individually(list(normalized))
                    else:
                        self._adapter.subscribe_markets(list(normalized))
        except Exception as exc:
            self.stop()
            self.error.emit(str(exc))

    @QtCore.pyqtSlot()
    def stop(self) -> None:
        adapter = self._adapter
        generation_id = self._generation_id
        stale_epics = frozenset((*self._epics, *self._chart_epics))
        self._adapter = None
        self._bridge = None
        self._generation_id = None
        self._epics = ()
        self._state = "disconnected"
        self._active_priority_count = 0
        self._chart_permission_fallback_attempted = False
        self._chart_permission_fallback_active = False
        self._chart_degraded_notice_emitted = False
        self._unavailable_chart_epics.clear()
        self._price_group_fallback_attempted = False
        self._price_group_fallback_active = False
        self._price_degraded_notice_emitted = False
        self._unavailable_price_epics.clear()
        if adapter is not None:
            try:
                adapter.stop()
            except Exception as exc:
                self.error.emit(str(exc))
        if generation_id is not None:
            self._runtime.mark_catalogue_stream_stale(
                generation_id=generation_id,
                epics=stale_epics,
                received_at_utc=self._now_provider(),
                reason_code="STREAM_STOPPED",
            )
            self._runtime.publish_stream_status(
                generation_id=generation_id,
                status="disconnected",
                observed_at_utc=self._now_provider(),
            )
        self.coverage_changed.emit("disconnected", 0, self._catalogue_total, 0)

    @QtCore.pyqtSlot(int, object)
    def _on_quote(self, generation_id: int, value: object) -> None:
        if (
            not isinstance(value, Quote)
            or generation_id != self._generation_id
            or value.epic not in self._epics
        ):
            return
        now = self._now_provider()
        if not self._runtime.publish_live_catalogue_quote(
            generation_id=generation_id,
            quote=value,
            received_at_utc=now,
        ):
            self.stop()
            return
        self.quote_received.emit(value)
        self._runtime.publish_stream_status(
            generation_id=generation_id,
            status="live",
            observed_at_utc=now,
        )
        self._state = "live"
        self.coverage_changed.emit(
            "live",
            self._coverage_count,
            self._catalogue_total,
            self._active_priority_count,
        )

    @QtCore.pyqtSlot(int, object)
    def _on_account_metrics(self, generation_id: int, value: object) -> None:
        if not isinstance(value, AccountMetricsUpdate) or generation_id != self._generation_id:
            return
        if not self._runtime.publish_account_metrics_update(
            generation_id=generation_id,
            update=value,
            received_at_utc=self._now_provider(),
        ):
            self.stop()
            return
        self._state = "live"
        self.coverage_changed.emit(
            "live",
            self._coverage_count,
            self._catalogue_total,
            self._active_priority_count,
        )

    @QtCore.pyqtSlot(int, object)
    def _on_chart(self, generation_id: int, value: object) -> None:
        if (
            not isinstance(value, ChartCandleUpdate)
            or generation_id != self._generation_id
            or value.epic not in self._chart_epics
        ):
            return
        now = self._now_provider()
        quote = _quote_from_chart(value)
        if quote is not None:
            self._runtime.publish_live_catalogue_quote(
                generation_id=generation_id,
                quote=quote,
                received_at_utc=now,
            )
            published_reference = self._runtime.publish_scanner_reference_quote(
                generation_id=generation_id,
                quote=quote,
                received_at_utc=now,
            )
            if published_reference:
                self.quote_received.emit(quote)
        self._runtime.publish_stream_status(
            generation_id=generation_id,
            status="live",
            observed_at_utc=now,
        )
        self._state = "live"
        self.chart_update_received.emit(value)
        self.coverage_changed.emit(
            "live",
            self._coverage_count,
            self._catalogue_total,
            self._active_priority_count,
        )

    @QtCore.pyqtSlot(int, str)
    def _on_status(self, generation_id: int, status: str) -> None:
        if generation_id != self._generation_id:
            return
        normalized = _normalize_stream_status(status)
        self._publish_status(normalized)

    @QtCore.pyqtSlot(int, str)
    def _on_error(self, generation_id: int, message: str) -> None:
        if generation_id != self._generation_id:
            return
        normalized = message.upper()
        if (
            not self._price_group_fallback_attempted
            and "SUBSCRIPTION ERROR FOR PRICE: 21 INVALID GROUP" in normalized
            and self._adapter is not None
        ):
            self._price_group_fallback_attempted = True
            # Individual callbacks may be synchronous. Activate the degraded mode before
            # resubscribing so one invalid market is isolated rather than failing the stream.
            self._price_group_fallback_active = True
            try:
                self._adapter.subscribe_markets_individually(list(self._epics))
            except Exception as exc:
                self._price_group_fallback_active = False
                self._publish_status("failed")
                self.error.emit(str(exc))
                return
            self._publish_status("subscribing")
            self.error.emit("stream.price_group_degraded")
            return
        invalid_price_epic = self._invalid_individual_price_epic(normalized)
        if invalid_price_epic is not None:
            if invalid_price_epic not in self._unavailable_price_epics:
                self._unavailable_price_epics.add(invalid_price_epic)
                priority_epics = frozenset(
                    (*self._priority_epics, *self._protected_epics, *self._tracked_epics)
                )
                if invalid_price_epic in priority_epics:
                    self._active_priority_count = max(0, self._active_priority_count - 1)
                self._runtime.mark_catalogue_stream_stale(
                    generation_id=generation_id,
                    epics=frozenset((invalid_price_epic,)),
                    received_at_utc=self._now_provider(),
                    reason_code="STREAM_INVALID_GROUP",
                )
                self.coverage_changed.emit(
                    self._state,
                    self._coverage_count,
                    self._catalogue_total,
                    self._active_priority_count,
                )
                if not self._price_degraded_notice_emitted:
                    self._price_degraded_notice_emitted = True
                    self.error.emit("stream.price_market_unavailable")
            return
        grouped_scope = f"CHART:{len(self._chart_epics)}-MARKETS:"
        if (
            len(self._chart_epics) > 1
            and not self._chart_permission_fallback_attempted
            and grouped_scope in normalized
            and "INSUFFICIENT PERMISSIONS" in normalized
            and self._adapter is not None
        ):
            self._chart_permission_fallback_attempted = True
            # Individual subscription callbacks may be delivered synchronously by an adapter.
            # Mark the fallback active first so a per-market denial is classified as degraded
            # CHART coverage instead of a fatal stream error.
            self._chart_permission_fallback_active = True
            try:
                subscribe_individually = getattr(
                    self._adapter,
                    "subscribe_charts_individually",
                    None,
                )
                if subscribe_individually is None:
                    self._adapter.subscribe_charts([self._chart_epics[0]], "1MINUTE")
                else:
                    subscribe_individually(list(self._chart_epics), "1MINUTE")
            except Exception as exc:
                self._chart_permission_fallback_active = False
                self._publish_status("failed")
                self.error.emit(str(exc))
                return
            self._publish_status("subscribing")
            self.error.emit("stream.chart_group_degraded")
            return
        denied_epic = self._denied_individual_chart_epic(normalized)
        if denied_epic is not None:
            if denied_epic not in self._unavailable_chart_epics:
                self._unavailable_chart_epics.add(denied_epic)
                self._active_priority_count = max(0, self._active_priority_count - 1)
                self._runtime.mark_catalogue_stream_stale(
                    generation_id=generation_id,
                    epics=frozenset((denied_epic,)),
                    received_at_utc=self._now_provider(),
                    reason_code="STREAM_PERMISSION_DENIED",
                )
                self.coverage_changed.emit(
                    self._state,
                    self._coverage_count,
                    self._catalogue_total,
                    self._active_priority_count,
                )
                if not self._chart_degraded_notice_emitted:
                    self._chart_degraded_notice_emitted = True
                    self.error.emit("stream.chart_market_unavailable")
                self.chart_market_unavailable.emit(denied_epic)
            return
        self._publish_status("failed")
        self.error.emit(message)

    def _denied_individual_chart_epic(self, normalized_message: str) -> str | None:
        if (
            not self._chart_permission_fallback_active
            or "INSUFFICIENT PERMISSIONS" not in normalized_message
        ):
            return None
        for epic in self._chart_epics:
            if f"CHART:{epic.upper()}:" in normalized_message:
                return epic
        return None

    def _invalid_individual_price_epic(self, normalized_message: str) -> str | None:
        if (
            not self._price_group_fallback_active
            or "21 INVALID GROUP" not in normalized_message
        ):
            return None
        for row in self._runtime.read_catalogue().rows:
            if row.epic and f"PRICE:{row.epic.upper()}:" in normalized_message:
                return row.epic
        return None

    def _publish_status(self, status: str) -> None:
        generation_id = self._generation_id
        if generation_id is None:
            return
        published = self._runtime.publish_stream_status(
            generation_id=generation_id,
            status=status,
            observed_at_utc=self._now_provider(),
        )
        if not published:
            self.stop()
            return
        self._state = status
        if status in {"disconnected", "failed", "stale"}:
            self._runtime.mark_catalogue_stream_stale(
                generation_id=generation_id,
                epics=frozenset((*self._epics, *self._chart_epics)),
                received_at_utc=self._now_provider(),
                reason_code=f"STREAM_{status.upper()}",
            )
        self.coverage_changed.emit(
            status,
            self._coverage_count,
            self._catalogue_total,
            self._active_priority_count,
        )

    @property
    def _coverage_count(self) -> int:
        return (
            len(self._epics)
            - len(frozenset(self._epics) & self._unavailable_price_epics)
            + len(self._chart_epics)
            - len(self._unavailable_chart_epics)
        )


# Compatibility name retained for imports created during the previous incremental lot.
SelectedMarketStreamController = CatalogueMarketStreamController


def _normalize_stream_status(status: str) -> str:
    normalized = status.strip().upper()
    if normalized.startswith("SUBSCRIBED"):
        return "subscribed_waiting_first_tick"
    if normalized.startswith("CONNECTED"):
        return "connected"
    if normalized.startswith("CONNECTING"):
        return "connecting"
    if normalized.startswith("RECONNECTING"):
        return "reconnecting"
    if normalized.startswith("SUBSCRIBING"):
        return "subscribing"
    if normalized.startswith("STALLED") or normalized == "STALE":
        return "stale"
    if normalized.startswith("DISCONNECTED") or normalized.startswith("UNSUBSCRIBED"):
        return "disconnected"
    if normalized == "LIVE":
        return "live"
    if normalized == "FAILED":
        return "failed"
    return normalized.lower() or "unknown"


def _quote_from_chart(update: ChartCandleUpdate) -> Quote | None:
    bid = _raw_float(update.raw.get("BID_CLOSE"))
    offer = _raw_float(update.raw.get("OFR_CLOSE"))
    if bid is None and offer is None and update.close is None:
        return None
    close = (
        (bid + offer) / 2.0
        if bid is not None and offer is not None
        else bid if bid is not None else offer if offer is not None else update.close
    )
    day_open = _raw_float(update.raw.get("DAY_OPEN_MID"))
    net_change = _raw_float(update.raw.get("DAY_NET_CHG_MID"))
    if net_change is None and close is not None and day_open is not None:
        net_change = close - day_open
    percent_change = _raw_float(update.raw.get("DAY_PERC_CHG_MID"))
    if percent_change is None and net_change is not None and day_open not in (None, 0.0):
        percent_change = net_change / day_open * 100.0
    return Quote(
        epic=update.epic,
        bid=bid if bid is not None else update.close,
        offer=offer if offer is not None else update.close,
        net_change=net_change,
        percent_change=percent_change,
        timestamp_ms=update.timestamp_ms,
        snapshot=update.snapshot,
        raw=update.raw,
    )


def _raw_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
