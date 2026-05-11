"""Lightstreamer-backed IG streaming adapter."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from trading_ig_assistant.adapters.ig_rest import IGSession
from trading_ig_assistant.domain.market_data import Quote

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
    "BID",
    "OFFER",
    "CHANGE",
    "CHANGE_PCT",
    "MARKET_STATE",
    "UPDATE_TIME",
    "UTM",
]


class StreamingEventSink(Protocol):
    def on_stream_status(self, status: str) -> None:
        """Receive Lightstreamer connection status."""

    def on_quote(self, quote: Quote) -> None:
        """Receive a normalized market quote."""

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
    _subscription: Any = field(default=None, init=False, repr=False)
    _current_epic: str | None = field(default=None, init=False, repr=False)

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
            if self._subscription is not None:
                self._client.unsubscribe(self._subscription)
        finally:
            self._subscription = None
            self._current_epic = None
            try:
                self._client.disconnect()
            finally:
                self._client = None
                self._emit_status("DISCONNECTED")

    def subscribe_market(self, epic: str) -> None:
        if self._client is None:
            self.start()
        if self._client is None:
            return
        if self._current_epic == epic and self._subscription is not None:
            return
        if self._subscription is not None:
            self._client.unsubscribe(self._subscription)
            self._subscription = None
        item_name = f"MARKET:{epic}"
        LOGGER.debug(
            "IG streaming subscribe market account=%s epic=%s item=%s",
            self._mask_account_id(self.account_id),
            epic,
            item_name,
        )
        subscription = Subscription("MERGE", [item_name], PRICE_FIELDS)
        subscription.addListener(_SubscriptionListener(self, epic))
        self._subscription = subscription
        self._current_epic = epic
        self._client.subscribe(subscription)

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
    def __init__(self, adapter: IGStreamingAdapter, epic: str) -> None:
        self._adapter = adapter
        self._epic = epic

    def onSubscription(self) -> None:  # noqa: N802
        self._adapter._handle_status(f"SUBSCRIBED:{self._epic}")

    def onUnsubscription(self) -> None:  # noqa: N802
        self._adapter._handle_status(f"UNSUBSCRIBED:{self._epic}")

    def onSubscriptionError(self, code: int, message: str) -> None:  # noqa: N802
        self._adapter._handle_subscription_error(code, message, self._epic)

    def onItemUpdate(self, update_info: Any) -> None:  # noqa: N802
        self._adapter._handle_quote_update(_quote_from_update(update_info, self._epic))


def _quote_from_update(update_info: Any, epic: str) -> Quote:
    fields = {}
    try:
        fields = dict(update_info.getFields())
    except Exception:  # pragma: no cover - defensive only
        fields = {}

    bid = _optional_float(_first_value(update_info, ["BID", "BIDPRICE1", "BIDPRICE"]))
    offer = _optional_float(_first_value(update_info, ["OFFER", "ASKPRICE1", "ASK"]))
    net_change = _optional_float(
        _first_value(update_info, ["CHANGE", "DAY_NET_CHG_MID", "NET_CHANGE"])
    )
    percent_change = _optional_float(
        _first_value(update_info, ["CHANGE_PCT", "DAY_PERC_CHG_MID", "PERCENT_CHANGE"])
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
