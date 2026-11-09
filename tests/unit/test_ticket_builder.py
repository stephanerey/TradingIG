from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.adapter_contracts import AccountRef, OrderDirection
from trading_ig_assistant.domain.positions import PaperFillAssumptions, PaperQuote
from trading_ig_assistant.services.ticket_builder import TicketBuilder, TicketValidationError

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
ACCOUNT = AccountRef("paper", "paper", "PAPER-A")
QUOTE = PaperQuote("WTI-PAPER", NOW, Decimal("100"), Decimal("101"), "EUR")
ASSUMPTIONS = PaperFillAssumptions(Decimal("1"), Decimal("0.5"), "fixture-v1")


def test_ticket_contains_net_estimates_and_simulation_warning() -> None:
    ticket = TicketBuilder().build(
        intent_id="INTENT-1",
        account=ACCOUNT,
        quote=QUOTE,
        underlying_id="WTI",
        direction=OrderDirection.BUY,
        quantity=Decimal("2"),
        stop=Decimal("96.5"),
        target=Decimal("111.5"),
        knockout=Decimal("90"),
        expires_at_utc=NOW + timedelta(hours=1),
        assumptions=ASSUMPTIONS,
        scanner_ranking=Decimal("80"),
        scanner_commentary="ranking, not a probability",
    )

    assert ticket.entry_price == Decimal("101.5")
    assert ticket.spread_cost == Decimal("2")
    assert ticket.fee_estimate == Decimal("4")
    assert ticket.slippage_estimate == Decimal("2.0")
    assert ticket.estimated_loss == Decimal("16.0")
    assert ticket.estimated_gain == Decimal("14.0")
    assert "PAPER_SIMULATION_ONLY" in ticket.warnings


def test_ticket_rejects_levels_that_contradict_direction() -> None:
    with pytest.raises(TicketValidationError, match="contradict"):
        TicketBuilder().build(
            intent_id="BAD",
            account=ACCOUNT,
            quote=QUOTE,
            underlying_id="WTI",
            direction=OrderDirection.BUY,
            quantity=Decimal("1"),
            stop=Decimal("105"),
            target=Decimal("110"),
            knockout=Decimal("90"),
            expires_at_utc=NOW + timedelta(hours=1),
            assumptions=ASSUMPTIONS,
        )


def test_ticket_builder_rejects_ig_account_scope() -> None:
    with pytest.raises(TicketValidationError, match="paper"):
        TicketBuilder().build(
            intent_id="LIVE",
            account=AccountRef("ig", "live", "LIVE-A"),
            quote=QUOTE,
            underlying_id="WTI",
            direction=OrderDirection.BUY,
            quantity=Decimal("1"),
            stop=Decimal("95"),
            target=None,
            knockout=None,
            expires_at_utc=NOW + timedelta(hours=1),
            assumptions=ASSUMPTIONS,
        )


def test_ticket_maps_to_risk_request_with_all_costs() -> None:
    ticket = TicketBuilder().build(
        intent_id="RISK",
        account=ACCOUNT,
        quote=QUOTE,
        underlying_id="WTI",
        direction=OrderDirection.SELL,
        quantity=Decimal("1"),
        stop=Decimal("105"),
        target=Decimal("90"),
        knockout=Decimal("110"),
        expires_at_utc=NOW + timedelta(hours=1),
        assumptions=ASSUMPTIONS,
    )

    request = TicketBuilder.risk_request(ticket, maximum_ko_loss=Decimal("12"))

    assert request.estimated_stop_loss == Decimal("5.5")
    assert request.anticipated_costs == Decimal("3")
    assert request.scenario_slippage == Decimal("1.0")
    assert request.maximum_ko_loss == Decimal("12")
