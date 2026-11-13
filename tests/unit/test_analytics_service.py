from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.journal import JournalEvent, PnlPeriod, PnlStatus
from trading_ig_assistant.services.analytics_service import (
    aggregate_realized_pnl,
    summarize_realized_trades,
)


def _pnl_event(
    event_id: str,
    timestamp: datetime,
    amount: Decimal | None,
    currency: str | None,
    status: PnlStatus,
) -> JournalEvent:
    return JournalEvent(
        event_id=event_id,
        timestamp_utc=timestamp,
        event_type="TRADE_EVENT",
        correlation_id=f"CORRELATION-{event_id}",
        account_ref="ACCOUNT-OPAQUE-1",
        payload={"fixture": True},
        pnl_amount=amount,
        pnl_currency=currency,
        pnl_status=status,
    )


def test_realized_pnl_totals_are_reproducible_by_period_and_currency() -> None:
    events = [
        _pnl_event(
            "WIN",
            datetime(2026, 10, 22, 10, 0, tzinfo=UTC),
            Decimal("10.25"),
            "EUR",
            PnlStatus.REALIZED,
        ),
        _pnl_event(
            "LOSS",
            datetime(2026, 10, 22, 14, 0, tzinfo=UTC),
            Decimal("-3.10"),
            "EUR",
            PnlStatus.REALIZED,
        ),
        _pnl_event(
            "ESTIMATE",
            datetime(2026, 10, 22, 15, 0, tzinfo=UTC),
            Decimal("99"),
            "EUR",
            PnlStatus.ESTIMATED,
        ),
        _pnl_event(
            "USD",
            datetime(2026, 10, 22, 16, 0, tzinfo=UTC),
            Decimal("2"),
            "USD",
            PnlStatus.REALIZED,
        ),
        _pnl_event(
            "CANCELLED",
            datetime(2026, 10, 22, 17, 0, tzinfo=UTC),
            None,
            None,
            PnlStatus.UNKNOWN,
        ),
    ]

    totals = aggregate_realized_pnl(events, timezone_name="UTC")
    eur = {(total.period, total.period_key): total for total in totals if total.currency == "EUR"}

    assert eur[(PnlPeriod.DAY, "2026-10-22")].amount == Decimal("7.15")
    assert eur[(PnlPeriod.DAY, "2026-10-22")].event_count == 2
    assert eur[(PnlPeriod.WEEK, "2026-W43")].amount == Decimal("7.15")
    assert eur[(PnlPeriod.MONTH, "2026-10")].amount == Decimal("7.15")
    assert eur[(PnlPeriod.YEAR, "2026")].amount == Decimal("7.15")
    usd_day = next(
        total for total in totals if total.currency == "USD" and total.period == PnlPeriod.DAY
    )
    assert usd_day.amount == Decimal("2")


def test_unknown_timezone_is_rejected_instead_of_silently_falling_back() -> None:
    with pytest.raises(ValueError, match="Unknown timezone"):
        aggregate_realized_pnl([], timezone_name="Invalid/Timezone")


def test_realized_trade_statistics_use_only_attested_paper_closures() -> None:
    start = datetime(2026, 10, 22, 10, 0, tzinfo=UTC)
    amounts = ("10", "-4", "2", "-6", "0")
    closures = tuple(
        replace(
            _pnl_event(
                f"CLOSE-{index}",
                start + timedelta(minutes=index),
                Decimal(amount),
                "EUR",
                PnlStatus.REALIZED,
            ),
            event_type="PAPER_POSITION_CLOSED",
        )
        for index, amount in enumerate(amounts)
    )
    unrelated = _pnl_event(
        "UNRELATED",
        start + timedelta(hours=1),
        Decimal("999"),
        "EUR",
        PnlStatus.REALIZED,
    )

    summary = summarize_realized_trades((*closures, unrelated))[0]

    assert summary.currency == "EUR"
    assert summary.trade_count == 5
    assert summary.win_count == 2
    assert summary.loss_count == 2
    assert summary.flat_count == 1
    assert summary.win_rate == Decimal("0.4")
    assert summary.profit_factor == Decimal("1.2")
    assert summary.max_drawdown == Decimal("8")
