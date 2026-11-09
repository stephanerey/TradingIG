"""Deterministic portfolio-risk checks with atomic opening reservations."""

from __future__ import annotations

from dataclasses import fields
from decimal import Decimal
from threading import Lock

from trading_ig_assistant.domain.risk import (
    OpeningReservation,
    PortfolioRiskSnapshot,
    ResolvedRiskSettings,
    RiskAction,
    RiskDecision,
    RiskDecisionStatus,
    RiskLimits,
    RiskRejectionReason,
    RiskRequest,
    RiskSettingsLayer,
)


def resolve_risk_settings(
    *,
    global_settings: RiskSettingsLayer | None = None,
    account_settings: RiskSettingsLayer | None = None,
    strategy_settings: RiskSettingsLayer | None = None,
    market_settings: RiskSettingsLayer | None = None,
) -> ResolvedRiskSettings:
    """Resolve settings in the approved global/account/strategy/market order."""

    defaults = RiskLimits()
    values = {field.name: getattr(defaults, field.name) for field in fields(RiskLimits)}
    sources = {field.name: "default" for field in fields(RiskLimits)}
    layers = (
        ("global", global_settings),
        ("account", account_settings),
        ("strategy", strategy_settings),
        ("market", market_settings),
    )
    for source, layer in layers:
        if layer is None:
            continue
        for field in fields(RiskSettingsLayer):
            value = getattr(layer, field.name)
            if value is not None:
                values[field.name] = value
                sources[field.name] = source
    limits = RiskLimits(**values)
    return ResolvedRiskSettings(limits=limits, sources=tuple(sources.items()))


class RiskEngine:
    """Evaluate openings and reserve their exposure capacity atomically.

    This service never calls a broker. Reservations are local, in-memory claims that a later
    coordinator must release after rejection, cancellation or reconciliation.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._reservations: dict[str, OpeningReservation] = {}

    def evaluate(
        self,
        request: RiskRequest,
        snapshot: PortfolioRiskSnapshot,
        settings: ResolvedRiskSettings | None = None,
    ) -> RiskDecision:
        with self._lock:
            return self._evaluate_locked(request, snapshot, settings or resolve_risk_settings())

    def evaluate_and_reserve(
        self,
        request: RiskRequest,
        snapshot: PortfolioRiskSnapshot,
        settings: ResolvedRiskSettings | None = None,
    ) -> RiskDecision:
        with self._lock:
            decision = self._evaluate_locked(
                request,
                snapshot,
                settings or resolve_risk_settings(),
            )
            if decision.approved and request.action == RiskAction.OPEN:
                self._reservations[request.intent_id] = OpeningReservation(
                    intent_id=request.intent_id,
                    account=request.account,
                    underlying_id=request.underlying_id,
                )
            return decision

    def release(self, intent_id: str) -> bool:
        with self._lock:
            return self._reservations.pop(intent_id, None) is not None

    def reservations(self) -> tuple[OpeningReservation, ...]:
        with self._lock:
            return tuple(self._reservations.values())

    def _evaluate_locked(
        self,
        request: RiskRequest,
        snapshot: PortfolioRiskSnapshot,
        settings: ResolvedRiskSettings,
    ) -> RiskDecision:
        account_state = snapshot.account_state(request.account)
        if account_state is None or not account_state.confirmed:
            return _rejected(RiskRejectionReason.ACCOUNT_UNCONFIRMED)

        if request.action != RiskAction.OPEN:
            return RiskDecision(status=RiskDecisionStatus.APPROVED)

        reasons: list[RiskRejectionReason] = []
        if not account_state.active_for_opening:
            reasons.append(RiskRejectionReason.ACCOUNT_INACTIVE)
        if not snapshot.exposure_complete:
            reasons.append(RiskRejectionReason.EXPOSURE_INCOMPLETE)
        if not request.price_fresh:
            reasons.append(RiskRejectionReason.STALE_PRICE)
        if not request.market_open:
            reasons.append(RiskRejectionReason.MARKET_CLOSED)
        if not request.product_supported:
            reasons.append(RiskRejectionReason.PRODUCT_UNSUPPORTED)

        duplicate_intent = request.intent_id in self._reservations or any(
            exposure.origin_intent_id == request.intent_id for exposure in snapshot.open_exposures
        )
        if duplicate_intent:
            reasons.append(RiskRejectionReason.DUPLICATE_INTENT)

        fx_rate = account_state.reference_currency_rate(snapshot.reference_currency)
        if fx_rate is None:
            reasons.append(RiskRejectionReason.FX_INCOMPLETE)

        budget_reference: Decimal | None = None
        estimated_loss_reference: Decimal | None = None
        if account_state.equity_reference_day <= 0 or account_state.equity_current <= 0:
            reasons.append(RiskRejectionReason.INVALID_EQUITY)
        elif fx_rate is not None:
            equity_basis = min(
                account_state.equity_reference_day,
                account_state.equity_current,
            )
            budget_reference = equity_basis * fx_rate * settings.limits.per_trade_fraction
            daily_loss = max(-account_state.daily_net_pnl, Decimal("0"))
            daily_limit = account_state.equity_reference_day * settings.limits.daily_loss_fraction
            if daily_loss >= daily_limit:
                reasons.append(RiskRejectionReason.DAILY_LOSS_LIMIT)

        if request.estimated_stop_loss is None:
            reasons.append(RiskRejectionReason.LOSS_ESTIMATE_UNKNOWN)
        elif fx_rate is not None:
            estimated_loss_reference = (
                request.estimated_stop_loss + request.anticipated_costs + request.scenario_slippage
            ) * fx_rate
            if budget_reference is not None and estimated_loss_reference > budget_reference:
                reasons.append(RiskRejectionReason.PER_TRADE_LIMIT)
            if (
                budget_reference is not None
                and request.maximum_ko_loss is not None
                and request.maximum_ko_loss * fx_rate > budget_reference
            ):
                reasons.append(RiskRejectionReason.KO_LOSS_LIMIT)

        active = (*snapshot.open_exposures, *self._reservations.values())
        if len(active) >= settings.limits.max_open_global:
            reasons.append(RiskRejectionReason.GLOBAL_EXPOSURE_LIMIT)
        underlying_count = sum(
            exposure.underlying_id == request.underlying_id for exposure in active
        )
        if underlying_count >= settings.limits.max_open_per_underlying:
            reasons.append(RiskRejectionReason.UNDERLYING_EXPOSURE_LIMIT)

        if reasons:
            return RiskDecision(
                status=RiskDecisionStatus.REJECTED,
                reasons=tuple(reasons),
                budget_reference=budget_reference,
                estimated_loss_reference=estimated_loss_reference,
            )
        return RiskDecision(
            status=RiskDecisionStatus.APPROVED,
            budget_reference=budget_reference,
            estimated_loss_reference=estimated_loss_reference,
        )


def _rejected(reason: RiskRejectionReason) -> RiskDecision:
    return RiskDecision(status=RiskDecisionStatus.REJECTED, reasons=(reason,))
