"""Build the V2 Paper dashboard from existing session and analytics contracts."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from trading_ig_assistant.app.projections.account import AccountHeaderVM
from trading_ig_assistant.app.projections.common import Amount, Availability, DataProvenance
from trading_ig_assistant.app.projections.dashboard import (
    DashboardVM,
    PositionRowVM,
    RealizedPnlVM,
    unavailable_amount,
)
from trading_ig_assistant.domain.journal import JournalEvent
from trading_ig_assistant.domain.positions import PaperPositionStatus
from trading_ig_assistant.services.analytics_service import (
    aggregate_realized_pnl,
    summarize_realized_trades,
)
from trading_ig_assistant.services.paper_session import PaperPositionSnapshot


def build_paper_dashboard_projection(
    *,
    generation_id: int,
    positions: tuple[PaperPositionSnapshot, ...],
    events: tuple[JournalEvent, ...],
    generated_at_utc: datetime,
) -> DashboardVM:
    open_positions = tuple(
        _position_row(generation_id, snapshot, generated_at_utc)
        for snapshot in positions
        if snapshot.position.status is PaperPositionStatus.OPEN
    )
    realized_pnl = tuple(
        RealizedPnlVM(
            period=total.period,
            period_key=total.period_key,
            amount=Amount(
                value=total.amount,
                currency=total.currency,
                provenance=DataProvenance(
                    source="paper-append-only-journal",
                    observed_at_utc=None,
                    received_at_utc=generated_at_utc,
                    scope="paper:local-paper-preview",
                    availability=Availability.READY,
                    reason_codes=("REALIZED_ONLY",),
                ),
            ),
            event_count=total.event_count,
        )
        for total in aggregate_realized_pnl(events)
    )
    statistics = summarize_realized_trades(events)
    summary = statistics[0] if len(statistics) == 1 else None
    drawdown = None
    if summary is not None:
        drawdown = Amount(
            value=summary.max_drawdown,
            currency=summary.currency,
            provenance=DataProvenance(
                source="paper-append-only-journal",
                observed_at_utc=None,
                received_at_utc=generated_at_utc,
                scope="paper:local-paper-preview:closed-trades",
                availability=Availability.READY,
                reason_codes=("REALIZED_PAPER_CLOSURES_ONLY",),
            ),
        )
    return DashboardVM(
        generation_id=generation_id,
        account_id="local-paper-preview",
        execution_mode="PAPER",
        generated_at_utc=generated_at_utc,
        availability=Availability.READY,
        equity=None,
        available_funds=None,
        realized_pnl=realized_pnl,
        open_positions=open_positions,
        win_rate=summary.win_rate if summary is not None else None,
        profit_factor=summary.profit_factor if summary is not None else None,
        drawdown=drawdown,
    )


def merge_account_metrics_into_dashboard(
    dashboard: DashboardVM,
    header: AccountHeaderVM,
) -> DashboardVM:
    if dashboard.generation_id != header.generation_id:
        raise ValueError("dashboard and account header generations must match")
    return replace(
        dashboard,
        generated_at_utc=header.generated_at_utc,
        broker_account_id=header.account_id,
        equity=header.equity,
        account_balance=header.account_balance,
        available_funds=header.available_funds,
        account_profit_loss=header.account_profit_loss,
        margin_deposit=header.margin_deposit,
    )


def _position_row(
    generation_id: int,
    snapshot: PaperPositionSnapshot,
    generated_at_utc: datetime,
) -> PositionRowVM:
    position = snapshot.position
    scope = f"paper:local-paper-preview:{position.position_id}"
    entry_provenance = DataProvenance(
        source=position.price_provenance,
        observed_at_utc=position.opened_at_utc,
        received_at_utc=generated_at_utc,
        scope=scope,
        availability=Availability.READY,
        reason_codes=(f"FILL_MODEL_{position.fill_model_version}",),
    )
    if snapshot.mark_price is None:
        mark_price = unavailable_amount(
            currency=position.currency,
            source="paper-session-quote",
            scope=scope,
            received_at_utc=generated_at_utc,
            reason_code="MISSING_OR_STALE_MARK",
        )
    else:
        mark_price = Amount(
            value=snapshot.mark_price,
            currency=position.currency,
            provenance=DataProvenance(
                source="paper-session-current-quote",
                observed_at_utc=None,
                received_at_utc=generated_at_utc,
                scope=scope,
                availability=Availability.READY,
                reason_codes=("SESSION_FRESHNESS_VALIDATED",),
            ),
            estimate=True,
        )
    if snapshot.net_pnl is None:
        net_pnl = unavailable_amount(
            currency=position.currency,
            source="paper-session-valuation",
            scope=scope,
            received_at_utc=generated_at_utc,
            reason_code="MISSING_OR_STALE_MARK",
        )
    else:
        net_pnl = Amount(
            value=snapshot.net_pnl,
            currency=position.currency,
            provenance=mark_price.provenance,
            estimate=True,
        )
    return PositionRowVM(
        generation_id=generation_id,
        environment="paper",
        account_id="local-paper-preview",
        execution_mode="PAPER",
        position_id=position.position_id,
        product_id=position.product_id,
        underlying_id=position.underlying_id,
        direction=position.direction.value,
        quantity=position.quantity,
        entry_price=Amount(
            value=position.entry_price,
            currency=position.currency,
            provenance=entry_provenance,
        ),
        mark_price=mark_price,
        net_pnl=net_pnl,
        current_stop=position.current_stop,
        target=position.target,
        knockout=position.knockout,
        status=position.status.value,
        opened_at_utc=position.opened_at_utc,
    )
