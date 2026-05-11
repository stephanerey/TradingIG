"""Lightstreamer-backed IG streaming adapter."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from trading_ig_assistant.adapters.ig_rest import IGSession
from trading_ig_assistant.domain.market_data import ChartCandleUpdate, Quote

try:  # pragma: no cover - exercised in runtime, not in unit tests
    from lightstreamer.client import (
        ClientListener,
        LightstreamerClient,
        Subscription,
        SubscriptionListener,
    )
except ImportError:  # pragma: no cover - keep import errors explicit at runtime
    ClientListener = object  # type: ignore[assignment]
    LightstreamerClient = None  # type: ignore[assignment]
    Subscription = None  # type: ignore[assignment]
    SubscriptionListener = object  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)
PRICE_FIELDS = [
    "MID_OPEN",
    "HIGH",
    "LOW",
    "BIDQUOTEID",
    "ASKQUOTEID",
    "BIDPRICE1",
    "ASKPRICE1",
    "BIDSIZE1",
    "ASKSIZE1",
    "CURRENCY0",
    "TIMESTAMP",
    "DLG_FLAG",
    "NET_CHG",
    "NET_CHG_PCT",
    "DELAY",
]
CHART_FIELDS = [
    "UTM",
    "DAY_OPEN_MID",
    "DAY_NET_CHG_MID",
    "DAY_PERC_CHG_MID",
    "DAY_HIGH",
    "DAY_LOW",
    "OFR_OPEN",
    "OFR_HIGH",
    "OFR_LOW",
    "OFR_CLOSE",
    "BID_OPEN",
    "BID_HIGH",
    "BID_LOW",
    "BID_CLOSE",
    "LTP_OPEN",
    "LTP_HIGH",
    "LTP_LOW",
    "LTP_CLOSE",
    "CONS_END",
    "CONS_TICK_COUNT",
    "LTV",
    "TTV",
]


class StreamingEventSink(Protocol):
    def on_stream_status(self, status: str) -> None:
        """Receive Lightstreamer connection status."""

    def on_quote(self, quote: Quote) -> None:
        """Receive a normalized market quote."""

    def on_chart(self, chart_update: ChartCandleUpdate) -> None:
        """Receive a normalized chart candle update."""

    def on_stream_error(self, message: str) -> None:
        """Receive a stream error message."""


@dataclass
class IGStreamingAdapter:
    session: IGSession
    account_id: str
    adapter_set: str | None = "DEFAULT"
    event_sink: StreamingEventSink | None = None
    client_factory: Callable[[str, str | None], Any] | None = None
    _client: Any = field(default=None, init=False, repr=False)
    _price_subscription: Any = field(default=None, init=False, repr=False)
    _chart_subscription: Any = field(default=None, init=False, repr=False)
    _current_epic: str | None = field(default=None, init=False, repr=False)
    _current_price_epics: tuple[str, ...] = field(default_factory=tuple, init=False, repr=False)

    def start(self) -> None:
        if self._client is not None:
            return
        if not self.session.lightstreamer_endpoint:
            raise RuntimeError("IG session does not expose a Lightstreamer endpoint.")
        client_factory = self.client_factory or self._default_client_factory
        self._client = client_factory(self.session.lightstreamer_endpoint, self.adapter_set)
        self._client.addListener(_ClientListener(self))
        self._client.connectionDetails.setUser(self.account_id)
        self._client.connectionDetails.setPassword(
            f"CST-{self.session.cst}|XST-{self.session.security_token}"
        )
        LOGGER.debug(
            "IG streaming connect start account=%s endpoint=%s",
            self._mask_account_id(self.account_id),
            self.session.lightstreamer_endpoint,
        )
        self._emit_status("CONNECTING")
        self._client.connect()

    def stop(self) -> None:
        if self._client is None:
            return
        LOGGER.debug(
            "IG streaming stop account=%s epic=%s",
            self._mask_account_id(self.account_id),
            self._current_epic or "<none>",
        )
        try:
            if self._price_subscription is not None:
                self._client.unsubscribe(self._price_subscription)
            if self._chart_subscription is not None:
                self._client.unsubscribe(self._chart_subscription)
        finally:
            self._price_subscription = None
            self._chart_subscription = None
            self._current_epic = None
            self._current_price_epics = ()
            try:
                self._client.disconnect()
            finally:
                self._client = None
                self._emit_status("DISCONNECTED")

    def subscribe_market(self, epic: str) -> None:
        self.subscribe_markets([epic])

    def subscribe_markets(self, epics: list[str]) -> None:
        if self._client is None:
            self.start()
        if self._client is None:
            return
        normalized_epics = tuple(dict.fromkeys(epic for epic in epics if epic))
        if not normalized_epics:
            return
        if self._current_price_epics == normalized_epics and self._price_subscription is not None:
            return
        if self._price_subscription is not None:
            self._client.unsubscribe(self._price_subscription)
            self._price_subscription = None
        item_names = [f"PRICE:{self.account_id}:{epic}" for epic in normalized_epics]
        LOGGER.debug(
            "IG streaming subscribe markets account=%s count=%s items=%s",
            self._mask_account_id(self.account_id),
            len(item_names),
            item_names,
        )
        subscription = Subscription("MERGE", item_names, PRICE_FIELDS)
        subscription.addListener(_SubscriptionListener(self))
        self._price_subscription = subscription
        self._current_price_epics = normalized_epics
        self._client.subscribe(subscription)

    def subscribe_chart(self, epic: str, scale: str = "1MINUTE") -> None:
        if self._client is None:
            self.start()
        if self._client is None:
            return
        if self._chart_subscription is not None:
            self._client.unsubscribe(self._chart_subscription)
            self._chart_subscription = None
        item_name = f"CHART:{epic}:{scale}"
        LOGGER.debug(
            "IG streaming subscribe chart account=%s epic=%s scale=%s item=%s",
            self._mask_account_id(self.account_id),
            epic,
            scale,
            item_name,
        )
        chart_subscription = Subscription("MERGE", [item_name], CHART_FIELDS)
        chart_subscription.addListener(_ChartSubscriptionListener(self, epic, scale))
        self._chart_subscription = chart_subscription
        self._current_epic = epic
        self._client.subscribe(chart_subscription)

    def _handle_status(self, status: str) -> None:
        LOGGER.debug(
            "IG streaming status account=%s status=%s epic=%s",
            self._mask_account_id(self.account_id),
            status,
            self._current_epic or "<none>",
        )
        self._emit_status(status)

    def _handle_server_error(self, code: int, message: str) -> None:
        error_message = f"Lightstreamer server error {code}: {message}"
        LOGGER.debug(
            "IG streaming server error account=%s error=%s",
            self._mask_account_id(self.account_id),
            error_message,
        )
        self._emit_error(error_message)

    def _handle_subscription_error(self, code: int, message: str, epic: str) -> None:
        error_message = f"Subscription error for {epic}: {code} {message}"
        LOGGER.debug(
            "IG streaming subscription error account=%s epic=%s error=%s",
            self._mask_account_id(self.account_id),
            epic,
            error_message,
        )
        self._emit_error(error_message)

    def _handle_quote_update(self, quote: Quote) -> None:
        LOGGER.debug(
            "IG streaming quote account=%s epic=%s bid=%s offer=%s change=%s pct=%s state=%s",
            self._mask_account_id(self.account_id),
            quote.epic,
            quote.bid,
            quote.offer,
            quote.net_change,
            quote.percent_change,
            quote.market_state,
        )
        self._emit_quote(quote)

    def _handle_chart_update(self, chart_update: ChartCandleUpdate) -> None:
        LOGGER.debug(
            "IG streaming chart account=%s epic=%s interval=%s open=%s high=%s low=%s "
            "close=%s end=%s",
            self._mask_account_id(self.account_id),
            chart_update.epic,
            chart_update.interval,
            chart_update.open,
            chart_update.high,
            chart_update.low,
            chart_update.close,
            chart_update.end_of_candle,
        )
        if self.event_sink is not None:
            self.event_sink.on_chart(chart_update)

    def _emit_status(self, status: str) -> None:
        if self.event_sink is not None:
            self.event_sink.on_stream_status(status)

    def _emit_quote(self, quote: Quote) -> None:
        if self.event_sink is not None:
            self.event_sink.on_quote(quote)

    def _emit_error(self, message: str) -> None:
        if self.event_sink is not None:
            self.event_sink.on_stream_error(message)

    @staticmethod
    def _default_client_factory(server_address: str, adapter_set: str | None) -> Any:
        if LightstreamerClient is None:
            raise RuntimeError(
                "lightstreamer-client-lib is not installed. Install the optional streaming "
                "dependency to enable live market data."
            )
        return LightstreamerClient(server_address, adapter_set)

    @staticmethod
    def _mask_account_id(account_id: str) -> str:
        if len(account_id) <= 4:
            return "****"
        return f"{account_id[:2]}...{account_id[-2:]}"


class _ClientListener(ClientListener):
    def __init__(self, adapter: IGStreamingAdapter) -> None:
        self._adapter = adapter

    def onStatusChange(self, status: str) -> None:  # noqa: N802
        self._adapter._handle_status(status)

    def onServerError(self, code: int, message: str) -> None:  # noqa: N802
        self._adapter._handle_server_error(code, message)


class _SubscriptionListener(SubscriptionListener):
    def __init__(self, adapter: IGStreamingAdapter) -> None:
        self._adapter = adapter

    def onSubscription(self) -> None:  # noqa: N802
        self._adapter._handle_status("SUBSCRIBED:PRICE")

    def onUnsubscription(self) -> None:  # noqa: N802
        self._adapter._handle_status("UNSUBSCRIBED:PRICE")

    def onSubscriptionError(self, code: int, message: str) -> None:  # noqa: N802
        self._adapter._handle_subscription_error(code, message, "PRICE")

    def onItemUpdate(self, update_info: Any) -> None:  # noqa: N802
        self._adapter._handle_quote_update(_quote_from_update(update_info))


class _ChartSubscriptionListener(SubscriptionListener):
    def __init__(self, adapter: IGStreamingAdapter, epic: str, interval: str) -> None:
        self._adapter = adapter
        self._epic = epic
        self._interval = interval

    def onSubscription(self) -> None:  # noqa: N802
        self._adapter._handle_status(f"SUBSCRIBED:CHART:{self._epic}:{self._interval}")

    def onUnsubscription(self) -> None:  # noqa: N802
        self._adapter._handle_status(f"UNSUBSCRIBED:CHART:{self._epic}:{self._interval}")

    def onSubscriptionError(self, code: int, message: str) -> None:  # noqa: N802
        self._adapter._handle_subscription_error(
            code,
            message,
            f"CHART:{self._epic}:{self._interval}",
        )

    def onItemUpdate(self, update_info: Any) -> None:  # noqa: N802
        self._adapter._handle_chart_update(
            _chart_update_from_update(update_info, self._epic, self._interval)
        )


def _quote_from_update(update_info: Any) -> Quote:
    fields = {}
    try:
        fields = dict(update_info.getFields())
    except Exception:  # pragma: no cover - defensive only
        fields = {}
    epic = _epic_from_update(update_info)

    bid = _optional_float(_first_value(update_info, ["BID", "BIDPRICE1", "BIDPRICE"]))
    offer = _optional_float(_first_value(update_info, ["OFFER", "ASKPRICE1", "ASK"]))
    net_change = _optional_float(
        _first_value(update_info, ["CHANGE", "DAY_NET_CHG_MID", "NET_CHG", "NET_CHANGE"])
    )
    percent_change = _optional_float(
        _first_value(
            update_info,
            ["CHANGE_PCT", "DAY_PERC_CHG_MID", "NET_CHG_PCT", "PERCENT_CHANGE"],
        )
    )
    market_state = _first_string(update_info, ["MARKET_STATE"])
    timestamp_ms = _optional_int(_first_value(update_info, ["UPDATE_TIME", "UTM"]))
    return Quote(
        epic=epic,
        bid=bid,
        offer=offer,
        net_change=net_change,
        percent_change=percent_change,
        market_state=market_state,
        timestamp_ms=timestamp_ms,
        snapshot=bool(getattr(update_info, "isSnapshot", lambda: False)()),
        raw=fields,
    )


def _epic_from_update(update_info: Any) -> str:
    try:
        item_name = update_info.getItemName()
    except Exception:
        item_name = None
    if not item_name:
        return ""
    parts = str(item_name).split(":")
    if parts and parts[0] == "PRICE" and len(parts) >= 3:
        return ":".join(parts[2:])
    if parts and parts[0] == "CHART" and len(parts) >= 2:
        return parts[1]
    return str(item_name)


def _chart_update_from_update(update_info: Any, epic: str, interval: str) -> ChartCandleUpdate:
    fields = {}
    try:
        fields = dict(update_info.getFields())
    except Exception:  # pragma: no cover - defensive only
        fields = {}
    return ChartCandleUpdate(
        epic=epic,
        interval=interval,
        timestamp_ms=_optional_int(_first_value(update_info, ["UTM"])),
        open=_optional_float(
            _first_value(
                update_info,
                ["BID_OPEN", "OFR_OPEN", "LTP_OPEN", "DAY_OPEN_MID"],
            )
        ),
        high=_optional_float(
            _first_value(update_info, ["BID_HIGH", "OFR_HIGH", "LTP_HIGH", "DAY_HIGH"])
        ),
        low=_optional_float(
            _first_value(update_info, ["BID_LOW", "OFR_LOW", "LTP_LOW", "DAY_LOW"])
        ),
        close=_optional_float(
            _first_value(update_info, ["BID_CLOSE", "OFR_CLOSE", "LTP_CLOSE"])
        ),
        volume=_optional_float(_first_value(update_info, ["LTV", "TTV"])),
        tick_count=_optional_int(_first_value(update_info, ["CONS_TICK_COUNT"])),
        end_of_candle=str(_first_value(update_info, ["CONS_END"])) == "1",
        snapshot=bool(getattr(update_info, "isSnapshot", lambda: False)()),
        raw=fields,
    )


def _first_value(update_info: Any, field_names: list[str]) -> Any:
    for field_name in field_names:
        try:
            value = update_info.getValue(field_name)
        except Exception:
            continue
        if value not in (None, ""):
            return value
    return None


def _first_string(update_info: Any, field_names: list[str]) -> str | None:
    value = _first_value(update_info, field_names)
    if value is None:
        return None
    return str(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None
