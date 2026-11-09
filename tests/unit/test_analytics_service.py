from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.journal import JournalEvent, PnlPeriod, PnlStatus
from trading_ig_assistant.services.analytics_service import aggregate_realized_pnl


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
