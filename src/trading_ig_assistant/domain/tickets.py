"""Validated paper-ticket models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from trading_ig_assistant.domain.adapter_contracts import OrderIntent


@dataclass(frozen=True)
class TicketDraft:
    intent: OrderIntent
    entry_price: Decimal
    spread_cost: Decimal
    fee_estimate: Decimal
    slippage_estimate: Decimal
    estimated_loss: Decimal
    estimated_gain: Decimal | None
    reward_risk_ratio: Decimal | None
    scanner_ranking: Decimal | None
    scanner_commentary: str
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.entry_price <= 0:
            raise ValueError("ticket entry_price must be positive")
        amounts = (
            self.spread_cost,
            self.fee_estimate,
            self.slippage_estimate,
            self.estimated_loss,
        )
        if any(amount < 0 for amount in amounts):
            raise ValueError("ticket cost and loss estimates must not be negative")
        if self.estimated_gain is not None and self.estimated_gain < 0:
            raise ValueError("ticket estimated gain must not be negative")
        if self.reward_risk_ratio is not None and self.reward_risk_ratio < 0:
            raise ValueError("ticket reward/risk ratio must not be negative")
        if self.scanner_ranking is not None and not Decimal("0") <= self.scanner_ranking <= Decimal(
            "100"
        ):
            raise ValueError("ticket scanner ranking must be between 0 and 100")
