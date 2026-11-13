"""Deterministic realized-P&L aggregation over immutable journal events."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from trading_ig_assistant.domain.journal import (
    JournalEvent,
    PnlPeriod,
    PnlStatus,
    PnlTotal,
)


@dataclass(frozen=True)
class RealizedTradeStatistics:
    currency: str
    trade_count: int
    win_count: int
    loss_count: int
    flat_count: int
    win_rate: Decimal
    profit_factor: Decimal | None
    max_drawdown: Decimal


def summarize_realized_trades(
    events: tuple[JournalEvent, ...] | list[JournalEvent],
) -> tuple[RealizedTradeStatistics, ...]:
    """Summarize only attested Paper closures, independently per currency."""

    grouped: defaultdict[str, list[JournalEvent]] = defaultdict(list)
    for event in events:
        if (
            event.event_type != "PAPER_POSITION_CLOSED"
            or event.pnl_status is not PnlStatus.REALIZED
            or event.pnl_amount is None
            or event.pnl_currency is None
        ):
            continue
        grouped[event.pnl_currency.upper()].append(event)

    summaries: list[RealizedTradeStatistics] = []
    for currency, currency_events in sorted(grouped.items()):
        ordered = sorted(currency_events, key=lambda event: event.timestamp_utc)
        values = tuple(event.pnl_amount for event in ordered if event.pnl_amount is not None)
        wins = tuple(value for value in values if value > 0)
        losses = tuple(value for value in values if value < 0)
        flats = len(values) - len(wins) - len(losses)
        gross_profit = sum(wins, start=Decimal("0"))
        gross_loss = abs(sum(losses, start=Decimal("0")))
        summaries.append(
            RealizedTradeStatistics(
                currency=currency,
                trade_count=len(values),
                win_count=len(wins),
                loss_count=len(losses),
                flat_count=flats,
                win_rate=Decimal(len(wins)) / Decimal(len(values)),
                profit_factor=(gross_profit / gross_loss if gross_loss else None),
                max_drawdown=_max_drawdown(values),
            )
        )
    return tuple(summaries)


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


def _max_drawdown(values: tuple[Decimal, ...]) -> Decimal:
    cumulative = Decimal("0")
    peak = Decimal("0")
    maximum = Decimal("0")
    for value in values:
        cumulative += value
        peak = max(peak, cumulative)
        maximum = max(maximum, peak - cumulative)
    return maximum
