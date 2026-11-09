"""Build validated, paper-only ticket drafts and matching risk requests."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from trading_ig_assistant.domain.adapter_contracts import AccountRef, OrderDirection, OrderIntent
from trading_ig_assistant.domain.positions import PaperFillAssumptions, PaperQuote
from trading_ig_assistant.domain.risk import RiskAction, RiskRequest
from trading_ig_assistant.domain.tickets import TicketDraft


class TicketValidationError(ValueError):
    """Raised when ticket levels are unsafe or internally contradictory."""


class TicketBuilder:
    def build(
        self,
        *,
        intent_id: str,
        account: AccountRef,
        quote: PaperQuote,
        underlying_id: str,
        direction: OrderDirection,
        quantity: Decimal,
        stop: Decimal,
        target: Decimal | None,
        knockout: Decimal | None,
        expires_at_utc: datetime,
        assumptions: PaperFillAssumptions,
        signal_id: str | None = None,
        scanner_ranking: Decimal | None = None,
        scanner_commentary: str = "",
    ) -> TicketDraft:
        if account.broker_id != "paper" or account.environment != "paper":
            raise TicketValidationError("R06 ticket builder accepts only paper accounts")
        if quantity <= 0:
            raise TicketValidationError("quantity must be positive")
        if not quote.fresh or not quote.market_open or not quote.product_supported:
            raise TicketValidationError("ticket requires fresh, open and supported paper quote")
        entry = quote.ask + assumptions.slippage_points_per_side
        if direction is OrderDirection.SELL:
            entry = quote.bid - assumptions.slippage_points_per_side
        self._validate_levels(direction, entry, stop, target, knockout)

        spread_cost = (quote.ask - quote.bid) * quantity
        fee_estimate = assumptions.fee_per_unit_per_side * quantity * Decimal("2")
        slippage_estimate = assumptions.slippage_points_per_side * quantity * Decimal("2")
        estimated_loss = abs(entry - stop) * quantity + fee_estimate + slippage_estimate
        estimated_gain = None
        reward_risk_ratio = None
        if target is not None:
            estimated_gain = max(
                abs(target - entry) * quantity - fee_estimate - slippage_estimate,
                Decimal("0"),
            )
            if estimated_loss > 0:
                reward_risk_ratio = estimated_gain / estimated_loss
        warnings = ["PAPER_SIMULATION_ONLY", "STOP_NOT_GUARANTEED_GAP_SLIPPAGE"]
        if knockout is None:
            warnings.append("KNOCKOUT_NOT_CONFIGURED")
        intent = OrderIntent(
            intent_id=intent_id,
            account=account,
            product_id=quote.product_id,
            underlying_id=underlying_id,
            direction=direction,
            quantity=quantity,
            requested_stop=stop,
            requested_target=target,
            requested_ko=knockout,
            signal_id=signal_id,
            expires_at_utc=expires_at_utc,
        )
        return TicketDraft(
            intent=intent,
            entry_price=entry,
            spread_cost=spread_cost,
            fee_estimate=fee_estimate,
            slippage_estimate=slippage_estimate,
            estimated_loss=estimated_loss,
            estimated_gain=estimated_gain,
            reward_risk_ratio=reward_risk_ratio,
            scanner_ranking=scanner_ranking,
            scanner_commentary=scanner_commentary,
            warnings=tuple(warnings),
        )

    @staticmethod
    def risk_request(ticket: TicketDraft, *, maximum_ko_loss: Decimal | None) -> RiskRequest:
        costs = ticket.spread_cost + ticket.fee_estimate
        stop_loss = abs(ticket.entry_price - ticket.intent.requested_stop) * ticket.intent.quantity
        return RiskRequest(
            intent_id=ticket.intent.intent_id,
            account=ticket.intent.account,
            underlying_id=ticket.intent.underlying_id,
            action=RiskAction.OPEN,
            estimated_stop_loss=stop_loss,
            anticipated_costs=costs,
            scenario_slippage=ticket.slippage_estimate,
            maximum_ko_loss=maximum_ko_loss,
            price_fresh=True,
            market_open=True,
            product_supported=True,
        )

    @staticmethod
    def _validate_levels(
        direction: OrderDirection,
        entry: Decimal,
        stop: Decimal,
        target: Decimal | None,
        knockout: Decimal | None,
    ) -> None:
        if entry <= 0 or stop <= 0:
            raise TicketValidationError("entry and stop must be positive")
        if direction is OrderDirection.BUY:
            valid = stop < entry and (target is None or target > entry)
            valid = valid and (knockout is None or knockout < entry)
        else:
            valid = stop > entry and (target is None or target < entry)
            valid = valid and (knockout is None or knockout > entry)
        if not valid:
            raise TicketValidationError("ticket stop/target/KO levels contradict direction")
