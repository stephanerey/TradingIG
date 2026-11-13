"""Build honest account and service-health projections from observed runtime state."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from trading_ig_assistant.app.projections.account import AccountHeaderVM
from trading_ig_assistant.app.projections.common import Amount, Availability, DataProvenance
from trading_ig_assistant.app.projections.health import HealthServiceVM
from trading_ig_assistant.domain.instruments import Account
from trading_ig_assistant.domain.market_data import AccountMetricsUpdate


def build_account_header_projection(
    *,
    generation_id: int,
    account: Account | None,
    environment: str | None,
    execution_mode: str,
    open_positions_count: int | None,
    rest_status: str,
    stream_status: str,
    ai_status: str,
    generated_at_utc: datetime,
) -> AccountHeaderVM:
    """Project identifiers and observed statuses without reclassifying broker balances."""

    currency = account.currency if account is not None and account.currency else None
    scope = f"ig-account:{account.account_id}" if account is not None else "ig-account:none"
    return AccountHeaderVM(
        generation_id=generation_id,
        account_id=account.account_id if account is not None else None,
        ig_environment=environment,
        product_account_type=account.account_type if account is not None else None,
        execution_mode=execution_mode,
        equity=None,
        available_funds=_account_amount(
            account.available if account is not None else None,
            currency=currency,
            scope=scope,
            generated_at_utc=generated_at_utc,
            field="AVAILABLE",
        ),
        day_pnl=None,
        week_pnl=None,
        month_pnl=None,
        open_positions_count=open_positions_count,
        ig_rest_status=rest_status,
        ig_stream_status=stream_status,
        ai_status=ai_status,
        generated_at_utc=generated_at_utc,
        account_balance=_account_amount(
            account.balance if account is not None else None,
            currency=currency,
            scope=scope,
            generated_at_utc=generated_at_utc,
            field="BALANCE",
        ),
        account_profit_loss=_account_amount(
            account.profit_loss if account is not None else None,
            currency=currency,
            scope=scope,
            generated_at_utc=generated_at_utc,
            field="PROFIT_LOSS",
        ),
        margin_deposit=_account_amount(
            account.deposit if account is not None else None,
            currency=currency,
            scope=scope,
            generated_at_utc=generated_at_utc,
            field="DEPOSIT",
        ),
    )


def merge_stream_account_metrics(
    header: AccountHeaderVM,
    update: AccountMetricsUpdate,
    *,
    received_at_utc: datetime,
) -> AccountHeaderVM:
    """Merge a partial ACCOUNT tick without erasing prior REST or stream values."""
    _require_utc(received_at_utc)
    if header.account_id != update.account_id:
        raise ValueError("account stream update does not match the active account")
    currency = _header_currency(header)
    scope = f"ig-account:{update.account_id}"

    def streamed(value: float | None, field: str, previous: Amount | None) -> Amount | None:
        if value is None or not currency:
            return previous
        return Amount(
            value=Decimal(str(value)),
            currency=currency,
            provenance=DataProvenance(
                source="ig-lightstreamer-account",
                observed_at_utc=None,
                received_at_utc=received_at_utc,
                scope=scope,
                availability=Availability.READY,
                reason_codes=(f"IG_ACCOUNT_{field}_STREAM",),
            ),
        )

    available = (
        update.available_to_deal if update.available_to_deal is not None else update.available_cash
    )
    margin = update.margin if update.margin is not None else update.deposit
    return replace(
        header,
        equity=streamed(update.equity, "EQUITY", header.equity),
        available_funds=streamed(available, "AVAILABLE_TO_DEAL", header.available_funds),
        account_balance=streamed(update.funds, "FUNDS", header.account_balance),
        account_profit_loss=streamed(
            update.profit_loss,
            "PNL",
            header.account_profit_loss,
        ),
        margin_deposit=streamed(margin, "MARGIN", header.margin_deposit),
        ig_stream_status="live",
        generated_at_utc=received_at_utc,
    )


def _header_currency(header: AccountHeaderVM) -> str | None:
    for amount in (
        header.equity,
        header.account_balance,
        header.available_funds,
        header.account_profit_loss,
        header.margin_deposit,
    ):
        if amount is not None and amount.currency:
            return amount.currency
    return None


def _account_amount(
    value: float | None,
    *,
    currency: str | None,
    scope: str,
    generated_at_utc: datetime,
    field: str,
) -> Amount | None:
    if value is None or not currency:
        return None
    return Amount(
        value=Decimal(str(value)),
        currency=currency,
        provenance=DataProvenance(
            source="ig-rest-accounts",
            observed_at_utc=None,
            received_at_utc=generated_at_utc,
            scope=scope,
            availability=Availability.READY,
            reason_codes=(f"IG_ACCOUNT_{field}_REST_SNAPSHOT",),
        ),
    )


def build_runtime_health_projection(
    *,
    generation_id: int,
    rest_status: str,
    stream_status: str,
    ai_status: str,
    observed_at_utc: datetime,
) -> tuple[HealthServiceVM, ...]:
    _require_utc(observed_at_utc)
    return (
        _health(
            generation_id,
            "ig-rest",
            rest_status,
            observed_at_utc,
            ready_values={"connected"},
        ),
        _health(
            generation_id,
            "ig-streaming",
            stream_status,
            observed_at_utc,
            ready_values={"live"},
        ),
        _health(
            generation_id,
            "openai",
            ai_status,
            observed_at_utc,
            ready_values={"available", "ready"},
        ),
    )


def _health(
    generation_id: int,
    service_id: str,
    status: str,
    observed_at_utc: datetime,
    *,
    ready_values: set[str],
) -> HealthServiceVM:
    normalized = status.strip().lower()
    if normalized in ready_values:
        availability = Availability.READY
    elif normalized in {
        "connected",
        "connecting",
        "subscribed",
        "subscribed_waiting_first_tick",
        "configured",
        "running",
    }:
        availability = Availability.WARMING_UP
    elif normalized == "stale":
        availability = Availability.STALE
    else:
        availability = Availability.UNAVAILABLE
    return HealthServiceVM(
        generation_id=generation_id,
        service_id=service_id,
        status=availability,
        summary=normalized or "unknown",
        observed_at_utc=observed_at_utc,
        reason_codes=(f"STATUS_{(normalized or 'unknown').upper()}",),
    )


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("projection timestamp must use UTC")
