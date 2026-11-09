"""Deterministic realized-P&L aggregation over immutable journal events."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from trading_ig_assistant.domain.journal import (
    JournalEvent,
    PnlPeriod,
    PnlStatus,
    PnlTotal,
)


def aggregate_realized_pnl(
    events: tuple[JournalEvent, ...] | list[JournalEvent],
    *,
    timezone_name: str = "UTC",
) -> tuple[PnlTotal, ...]:
    """Return day/week/month/year totals without cross-currency conversion."""

    if timezone_name.upper() in {"UTC", "ETC/UTC", "GMT"}:
        timezone = UTC
    else:
        try:
            timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown timezone {timezone_name!r}.") from exc

    amounts: defaultdict[tuple[PnlPeriod, str, str], Decimal] = defaultdict(Decimal)
    counts: defaultdict[tuple[PnlPeriod, str, str], int] = defaultdict(int)
    for event in events:
        if event.pnl_status != PnlStatus.REALIZED or event.pnl_amount is None:
            continue
        if event.pnl_currency is None:
            continue
        local_timestamp = event.timestamp_utc.astimezone(timezone)
        keys = {
            PnlPeriod.DAY: local_timestamp.strftime("%Y-%m-%d"),
            PnlPeriod.WEEK: (
                f"{local_timestamp.isocalendar().year}-W{local_timestamp.isocalendar().week:02d}"
            ),
            PnlPeriod.MONTH: local_timestamp.strftime("%Y-%m"),
            PnlPeriod.YEAR: local_timestamp.strftime("%Y"),
        }
        for period, period_key in keys.items():
            group = (period, period_key, event.pnl_currency.upper())
            amounts[group] += event.pnl_amount
            counts[group] += 1

    return tuple(
        PnlTotal(
            period=period,
            period_key=period_key,
            currency=currency,
            amount=amounts[(period, period_key, currency)],
            event_count=counts[(period, period_key, currency)],
        )
        for period, period_key, currency in sorted(
            amounts,
            key=lambda group: (group[0].value, group[1], group[2]),
        )
    )
