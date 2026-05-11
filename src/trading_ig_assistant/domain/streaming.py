"""Streaming domain models and subscription specs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class StreamState(StrEnum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    SUBSCRIBING = "SUBSCRIBING"
    SUBSCRIBED_WAITING_FIRST_TICK = "SUBSCRIBED_WAITING_FIRST_TICK"
    LIVE = "LIVE"
    STALE = "STALE"
    RECONNECTING = "RECONNECTING"
    FAILED = "FAILED"


@dataclass(frozen=True)
class StreamSubscriptionSpec:
    name: str
    item_template: str
    fields: tuple[str, ...]
    kind: str
    mode: str = "MERGE"
    scale: str | None = None

    def render_item(
        self,
        *,
        epic: str,
        account_id: str | None = None,
        scale: str | None = None,
    ) -> str:
        values = {
            "epic": epic,
            "account_id": account_id or "",
            "scale": scale or self.scale or "",
        }
        return self.item_template.format(**values)


@dataclass
class StreamDiagnosticResult:
    spec_name: str
    item: str
    fields: tuple[str, ...]
    state: StreamState = StreamState.DISCONNECTED
    connected: bool = False
    subscribed: bool = False
    first_update_received: bool = False
    first_update_latency_seconds: float | None = None
    update_count: int = 0
    sample_raw_fields: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


MARKET_QUOTE_FIELDS: tuple[str, ...] = (
    "BID",
    "OFFER",
    "UPDATE_TIME",
    "MARKET_STATE",
    "CHANGE",
    "CHANGE_PCT",
)

PRICE_QUOTE_FIELDS: tuple[str, ...] = (
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
)

CHART_CANDLE_FIELDS: tuple[str, ...] = (
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
)

GENERIC_QUOTE_FIELDS: tuple[str, ...] = tuple(
    dict.fromkeys([*MARKET_QUOTE_FIELDS, *PRICE_QUOTE_FIELDS])
)

MARKET_QUOTE_SPEC = StreamSubscriptionSpec(
    name="MARKET",
    item_template="MARKET:{epic}",
    fields=MARKET_QUOTE_FIELDS,
    kind="quote",
)

PRICE_QUOTE_SPEC = StreamSubscriptionSpec(
    name="PRICE",
    item_template="PRICE:{account_id}:{epic}",
    fields=PRICE_QUOTE_FIELDS,
    kind="quote",
)

CHART_CANDLE_SPEC = StreamSubscriptionSpec(
    name="CHART",
    item_template="CHART:{epic}:{scale}",
    fields=CHART_CANDLE_FIELDS,
    kind="chart",
    scale="1MINUTE",
)
