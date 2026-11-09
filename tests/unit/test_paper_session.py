import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.adapter_contracts import ExecutionStatus, OrderDirection
from trading_ig_assistant.domain.market_data import Quote
from trading_ig_assistant.domain.positions import PaperFillAssumptions, PaperQuote
from trading_ig_assistant.domain.risk import (
    AccountRiskState,
    PortfolioRiskSnapshot,
    RiskSettingsLayer,
)
from trading_ig_assistant.persistence.paper_session_codec import (
    decode_paper_session_state,
    encode_paper_session_state,
)
from trading_ig_assistant.services.paper_session import (
    LOCAL_PAPER_ACCOUNT,
    PaperSessionService,
    PaperTicketSubmission,
)
from trading_ig_assistant.services.risk_engine import resolve_risk_settings
from trading_ig_assistant.services.ticket_builder import TicketBuilder

NOW = datetime(2026, 10, 23, 15, 0, tzinfo=UTC)


def _submission(
    intent_id: str = "GUI-PAPER-1",
    *,
    observed_at: datetime = NOW,
    target: str = "105",
) -> PaperTicketSubmission:
    quote = PaperQuote(
        product_id="PAPER.EUR.ONE",
        observed_at_utc=observed_at,
        bid=Decimal("100"),
        ask=Decimal("101"),
        currency="EUR",
        provenance="fixture:paper-session",
    )
    assumptions = PaperFillAssumptions(
        fee_per_unit_per_side=Decimal("0.1"),
        slippage_points_per_side=Decimal("0.1"),
        model_version="paper-session-test-v1",
    )
    ticket = TicketBuilder().build(
        intent_id=intent_id,
        account=LOCAL_PAPER_ACCOUNT,
        quote=quote,
        underlying_id="PAPER.EUR.ONE",
        direction=OrderDirection.BUY,
        quantity=Decimal("1"),
        stop=Decimal("95"),
        target=Decimal(target),
        knockout=None,
        expires_at_utc=observed_at + timedelta(minutes=15),
        assumptions=assumptions,
    )
    return PaperTicketSubmission(
        ticket=ticket,
        risk_request=TicketBuilder.risk_request(ticket, maximum_ko_loss=None),
        risk_snapshot=PortfolioRiskSnapshot(
            reference_currency="EUR",
            accounts=(
                AccountRiskState(
                    account=LOCAL_PAPER_ACCOUNT,
                    currency="EUR",
                    equity_reference_day=Decimal("10000"),
                    equity_current=Decimal("10000"),
                    daily_net_pnl=Decimal("0"),
                    confirmed=True,
                ),
            ),
        ),
        risk_settings=resolve_risk_settings(),
        quote=quote,
        assumptions=assumptions,
    )


def test_paper_session_records_one_idempotent_local_submission() -> None:
    session = PaperSessionService()
    submission = _submission()

    first = session.submit(submission)
    duplicate = session.submit(submission)

    assert first == duplicate
    assert first.outcome.execution_result.status is ExecutionStatus.CONFIRMED
    assert len(session.position_snapshots()) == 1
    assert len(session.orders()) == 1
    assert [event.event_type for event in session.events()] == [
        "PAPER_PROPOSAL_SUBMITTED",
        "PAPER_POSITION_OPENED",
    ]
    assert len(session.open_exposures()) == 1


def test_paper_session_quote_closes_target_and_allows_next_opening() -> None:
    session = PaperSessionService()
    session.submit(_submission())

    results = session.process_market_quote(
        Quote(
            epic="PAPER.EUR.ONE",
            bid=105.0,
            offer=106.0,
            market_state="TRADEABLE",
        ),
        observed_at_utc=NOW + timedelta(minutes=1),
    )

    assert results[0].status is ExecutionStatus.CONFIRMED
    assert session.open_exposures() == ()
    closed = session.position_snapshots()[0]
    assert closed.position.status.value == "closed"
    assert closed.net_pnl == closed.position.realized_pnl
    assert session.events()[-1].event_type == "PAPER_POSITION_CLOSED"

    second = session.submit(
        _submission(
            "GUI-PAPER-2",
            observed_at=NOW + timedelta(minutes=2),
            target="110",
        )
    )
    assert second.outcome.execution_result.status is ExecutionStatus.CONFIRMED


def test_delayed_quote_cannot_trigger_or_manually_close_paper_position() -> None:
    clock = [NOW + timedelta(minutes=1)]
    session = PaperSessionService(now_provider=lambda: clock[0])
    opened = session.submit(_submission())
    position_id = opened.outcome.execution_result.broker_reference or ""
    results = session.process_market_quote(
        Quote(
            epic="PAPER.EUR.ONE",
            bid=105.0,
            offer=106.0,
            market_state="TRADEABLE",
            raw={"DELAY": "1"},
        ),
        observed_at_utc=NOW + timedelta(minutes=1),
    )
    assert results == ()
    assert session.position_snapshots()[0].mark_price is None
    closed = session.close_position(position_id)
    assert closed.status is ExecutionStatus.REJECTED
    assert closed.message == "STALE_PRICE"
    assert len(session.open_exposures()) == 1
    clock[0] = NOW + timedelta(minutes=2)
    session.process_market_quote(
        Quote(
            epic="PAPER.EUR.ONE", bid=102, offer=103, market_state="TRADEABLE", raw={"DELAY": "0"}
        ),
        observed_at_utc=NOW + timedelta(minutes=2),
    )
    assert session.close_position(position_id).status is ExecutionStatus.CONFIRMED


def test_paper_session_audits_stop_tightening_and_manual_close() -> None:
    session = PaperSessionService(now_provider=lambda: NOW + timedelta(minutes=1))
    opened = session.submit(_submission())
    position_id = opened.outcome.execution_result.broker_reference or ""

    widened = session.move_stop(position_id, Decimal("94"))
    tightened = session.move_stop(position_id, Decimal("100"))

    assert widened.status is ExecutionStatus.REJECTED
    assert widened.message == "STOP_WIDENING_FORBIDDEN"
    assert tightened.status is ExecutionStatus.CONFIRMED
    assert session.position_snapshots()[0].position.current_stop == Decimal("100")
    assert [event.event_type for event in session.events()][-2:] == [
        "PAPER_STOP_UPDATE_REJECTED",
        "PAPER_STOP_CONFIRMED",
    ]

    session.process_market_quote(
        Quote(epic="PAPER.EUR.ONE", bid=101, offer=102, market_state="TRADEABLE"),
        observed_at_utc=NOW + timedelta(minutes=1),
    )

    closed = session.close_position(position_id)

    assert closed.status is ExecutionStatus.CONFIRMED
    snapshot = session.position_snapshots()[0]
    assert snapshot.position.status.value == "closed"
    assert snapshot.position.exit_reason.value == "manual"
    assert session.open_exposures() == ()
    assert session.events()[-1].event_type == "PAPER_POSITION_CLOSED"


def test_paper_session_ignores_untracked_market_quote() -> None:
    session = PaperSessionService()

    results = session.process_market_quote(
        Quote(epic="OTHER", bid=1.0, offer=2.0, market_state="TRADEABLE"),
        observed_at_utc=NOW,
    )

    assert results == ()
    assert session.events() == ()


def test_paper_mark_and_manual_close_require_recent_nonfuture_quote() -> None:
    clock = [NOW + timedelta(seconds=30)]
    session = PaperSessionService(now_provider=lambda: clock[0])
    opened = session.submit(_submission())
    position_id = opened.outcome.execution_result.broker_reference or ""
    assert session.position_snapshots()[0].mark_price is not None

    clock[0] = NOW + timedelta(seconds=31)
    assert session.position_snapshots()[0].mark_price is None
    assert session.close_position(position_id).message == "STALE_PRICE"

    clock[0] = NOW - timedelta(seconds=1)
    assert session.position_snapshots()[0].mark_price is None
    assert session.close_position(position_id).message == "STALE_PRICE"
    assert len(session.open_exposures()) == 1


def test_connection_invalidation_cannot_close_at_previous_session_price() -> None:
    clock = [NOW + timedelta(seconds=10)]
    session = PaperSessionService(now_provider=lambda: clock[0])
    opened = session.submit(_submission())
    position_id = opened.outcome.execution_result.broker_reference or ""
    assert session.position_snapshots()[0].mark_price is not None
    session.invalidate_market_quotes()
    assert session.position_snapshots()[0].mark_price is None
    assert session.close_position(position_id).message == "STALE_PRICE"
    assert len(session.open_exposures()) == 1

    clock[0] += timedelta(seconds=1)
    session.process_market_quote(
        Quote(epic="PAPER.EUR.ONE", bid=102, offer=103, market_state="TRADEABLE"),
        observed_at_utc=clock[0],
    )
    assert session.close_position(position_id).status is ExecutionStatus.CONFIRMED


def test_paper_session_reuses_the_exact_preview_risk_settings() -> None:
    session = PaperSessionService()
    submission = _submission()
    conservative = replace(
        submission,
        risk_settings=resolve_risk_settings(
            global_settings=RiskSettingsLayer(per_trade_fraction=Decimal("0.0001"))
        ),
    )

    record = session.submit(conservative)

    assert record.outcome.execution_result.status is ExecutionStatus.REJECTED
    assert "per_trade_limit" in (record.outcome.execution_result.message or "")
    assert session.position_snapshots() == ()
    assert session.events()[-1].event_type == "PAPER_EXECUTION_REJECTED"


def test_paper_session_checkpoint_round_trip_restores_open_risk_and_can_close() -> None:
    session = PaperSessionService(now_provider=lambda: NOW + timedelta(minutes=1))
    opened = session.submit(_submission())
    position_id = opened.outcome.execution_result.broker_reference or ""
    session.move_stop(position_id, Decimal("100"))

    payload = encode_paper_session_state(session.checkpoint_state())
    transported = json.loads(json.dumps(payload))
    restored = PaperSessionService.from_checkpoint_state(
        decode_paper_session_state(transported),
        now_provider=lambda: NOW + timedelta(minutes=2),
    )

    assert restored.session_id == session.session_id
    assert restored.position_snapshots()[0].position.current_stop == Decimal("100")
    assert len(restored.open_exposures()) == 1
    closed = restored.close_position(position_id)
    assert closed.status is ExecutionStatus.REJECTED
    assert closed.message == "STALE_PRICE"
    restored.process_market_quote(
        Quote(epic="PAPER.EUR.ONE", bid=101, offer=102, market_state="TRADEABLE"),
        observed_at_utc=NOW + timedelta(minutes=2),
    )
    closed = restored.close_position(position_id)
    assert closed.status is ExecutionStatus.CONFIRMED
    assert restored.open_exposures() == ()
    second = restored.submit(
        _submission(
            "GUI-PAPER-AFTER-RESTORE",
            observed_at=NOW + timedelta(minutes=3),
            target="110",
        )
    )
    assert second.outcome.execution_result.status is ExecutionStatus.CONFIRMED


def test_paper_checkpoint_uses_decimal_text_and_rejects_unknown_format() -> None:
    session = PaperSessionService()
    session.submit(_submission())
    payload = encode_paper_session_state(session.checkpoint_state())

    assert payload["positions"][0]["entry_price"] == "101.1"
    assert "api_key" not in json.dumps(payload).lower()
    payload["format_version"] = 2
    with pytest.raises(ValueError, match="Unsupported"):
        decode_paper_session_state(payload)
