"""Broker-independent account and portfolio-risk models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from trading_ig_assistant.domain.adapter_contracts import AccountRef


class RiskAction(StrEnum):
    OPEN = "open"
    REDUCE = "reduce"
    CLOSE = "close"


class RiskDecisionStatus(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class RiskRejectionReason(StrEnum):
    ACCOUNT_UNCONFIRMED = "account_unconfirmed"
    ACCOUNT_INACTIVE = "account_inactive"
    FX_INCOMPLETE = "fx_incomplete"
    EXPOSURE_INCOMPLETE = "exposure_incomplete"
    INVALID_EQUITY = "invalid_equity"
    LOSS_ESTIMATE_UNKNOWN = "loss_estimate_unknown"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    PER_TRADE_LIMIT = "per_trade_limit"
    KO_LOSS_LIMIT = "ko_loss_limit"
    GLOBAL_EXPOSURE_LIMIT = "global_exposure_limit"
    UNDERLYING_EXPOSURE_LIMIT = "underlying_exposure_limit"
    DUPLICATE_INTENT = "duplicate_intent"
    STALE_PRICE = "stale_price"
    MARKET_CLOSED = "market_closed"
    PRODUCT_UNSUPPORTED = "product_unsupported"


@dataclass(frozen=True)
class RiskLimits:
    per_trade_fraction: Decimal = Decimal("0.01")
    daily_loss_fraction: Decimal = Decimal("0.03")
    max_open_global: int = 1
    max_open_per_underlying: int = 1

    def __post_init__(self) -> None:
        if not Decimal("0") <= self.per_trade_fraction <= Decimal("1"):
            raise ValueError("per_trade_fraction must be between 0 and 1")
        if not Decimal("0") <= self.daily_loss_fraction <= Decimal("1"):
            raise ValueError("daily_loss_fraction must be between 0 and 1")
        if self.max_open_global < 0:
            raise ValueError("max_open_global must not be negative")
        if self.max_open_per_underlying < 0:
            raise ValueError("max_open_per_underlying must not be negative")


@dataclass(frozen=True)
class RiskSettingsLayer:
    per_trade_fraction: Decimal | None = None
    daily_loss_fraction: Decimal | None = None
    max_open_global: int | None = None
    max_open_per_underlying: int | None = None


@dataclass(frozen=True)
class ResolvedRiskSettings:
    limits: RiskLimits
    sources: tuple[tuple[str, str], ...]

    def source_for(self, field_name: str) -> str:
        try:
            return dict(self.sources)[field_name]
        except KeyError as exc:
            raise KeyError(f"Unknown risk setting {field_name!r}") from exc


@dataclass(frozen=True)
class AccountRiskState:
    account: AccountRef
    currency: str
    equity_reference_day: Decimal
    equity_current: Decimal
    daily_net_pnl: Decimal
    confirmed: bool
    active_for_opening: bool = True
    fx_rate_to_reference: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.currency.strip():
            raise ValueError("currency is required")

    def reference_currency_rate(self, reference_currency: str) -> Decimal | None:
        if self.currency.upper() == reference_currency.upper():
            return Decimal("1")
        if self.fx_rate_to_reference is None or self.fx_rate_to_reference <= 0:
            return None
        return self.fx_rate_to_reference


@dataclass(frozen=True)
class ExposureState:
    exposure_id: str
    account: AccountRef
    underlying_id: str
    origin_intent_id: str | None = None

    def __post_init__(self) -> None:
        if not self.exposure_id.strip():
            raise ValueError("exposure_id is required")
        if not self.underlying_id.strip():
            raise ValueError("underlying_id is required")


@dataclass(frozen=True)
class PortfolioRiskSnapshot:
    reference_currency: str
    accounts: tuple[AccountRiskState, ...]
    open_exposures: tuple[ExposureState, ...] = ()
    exposure_complete: bool = True

    def __post_init__(self) -> None:
        if not self.reference_currency.strip():
            raise ValueError("reference_currency is required")
        account_refs = [state.account for state in self.accounts]
        if len(set(account_refs)) != len(account_refs):
            raise ValueError("portfolio contains duplicate account states")

    def account_state(self, account: AccountRef) -> AccountRiskState | None:
        return next((state for state in self.accounts if state.account == account), None)


@dataclass(frozen=True)
class RiskRequest:
    intent_id: str
    account: AccountRef
    underlying_id: str
    action: RiskAction
    estimated_stop_loss: Decimal | None = None
    anticipated_costs: Decimal = Decimal("0")
    scenario_slippage: Decimal = Decimal("0")
    maximum_ko_loss: Decimal | None = None
    price_fresh: bool = True
    market_open: bool = True
    product_supported: bool = True

    def __post_init__(self) -> None:
        if not self.intent_id.strip():
            raise ValueError("intent_id is required")
        if not self.underlying_id.strip():
            raise ValueError("underlying_id is required")
        amounts = (
            self.estimated_stop_loss,
            self.anticipated_costs,
            self.scenario_slippage,
            self.maximum_ko_loss,
        )
        if any(amount is not None and amount < 0 for amount in amounts):
            raise ValueError("risk amounts must not be negative")


@dataclass(frozen=True)
class RiskDecision:
    status: RiskDecisionStatus
    reasons: tuple[RiskRejectionReason, ...] = ()
    budget_reference: Decimal | None = None
    estimated_loss_reference: Decimal | None = None

    @property
    def approved(self) -> bool:
        return self.status == RiskDecisionStatus.APPROVED


@dataclass(frozen=True)
class OpeningReservation:
    intent_id: str
    account: AccountRef
    underlying_id: str
