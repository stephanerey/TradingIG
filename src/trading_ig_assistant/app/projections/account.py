"""Read-only account header projection for the persistent GUI shell."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from trading_ig_assistant.app.projections.common import Amount


@dataclass(frozen=True)
class AccountHeaderVM:
    generation_id: int
    account_id: str | None
    ig_environment: str | None
    product_account_type: str | None
    execution_mode: str
    equity: Amount | None
    available_funds: Amount | None
    day_pnl: Amount | None
    week_pnl: Amount | None
    month_pnl: Amount | None
    open_positions_count: int | None
    ig_rest_status: str
    ig_stream_status: str
    ai_status: str
    generated_at_utc: datetime
    account_balance: Amount | None = None
    account_profit_loss: Amount | None = None
    margin_deposit: Amount | None = None

    def __post_init__(self) -> None:
        if self.generation_id < 0:
            raise ValueError("generation_id must be non-negative")
        if not self.execution_mode.strip():
            raise ValueError("execution_mode is required")
        if self.open_positions_count is not None and self.open_positions_count < 0:
            raise ValueError("open_positions_count must be non-negative")
        if self.generated_at_utc.tzinfo is None or (
            self.generated_at_utc.utcoffset() != UTC.utcoffset(self.generated_at_utc)
        ):
            raise ValueError("generated_at_utc must use UTC")
