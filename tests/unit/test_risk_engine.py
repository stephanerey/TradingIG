from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from trading_ig_assistant.domain.adapter_contracts import AccountRef
from trading_ig_assistant.domain.risk import (
    AccountRiskState,
    ExposureState,
    PortfolioRiskSnapshot,
    RiskAction,
    RiskDecisionStatus,
    RiskRejectionReason,
    RiskRequest,
    RiskSettingsLayer,
)
from trading_ig_assistant.services.risk_engine import RiskEngine, resolve_risk_settings

ACCOUNT = AccountRef(broker_id="fake", environment="paper", account_id="ACCOUNT-A")


def _snapshot(
    *,
    currency: str = "EUR",
    fx_rate: Decimal | None = None,
    daily_pnl: Decimal = Decimal("0"),
    open_exposures: tuple[ExposureState, ...] = (),
    exposure_complete: bool = True,
) -> PortfolioRiskSnapshot:
    return PortfolioRiskSnapshot(
        reference_currency="EUR",
        accounts=(
            AccountRiskState(
                account=ACCOUNT,
                currency=currency,
                equity_reference_day=Decimal("1000"),
                equity_current=Decimal("1000"),
                daily_net_pnl=daily_pnl,
                confirmed=True,
                fx_rate_to_reference=fx_rate,
            ),
        ),
        open_exposures=open_exposures,
        exposure_complete=exposure_complete,
    )


def _opening(intent_id: str = "INTENT-1", underlying: str = "CRUDE-OIL") -> RiskRequest:
    return RiskRequest(
        intent_id=intent_id,
        account=ACCOUNT,
        underlying_id=underlying,
        action=RiskAction.OPEN,
        estimated_stop_loss=Decimal("8"),
        anticipated_costs=Decimal("1"),
        scenario_slippage=Decimal("1"),
    )


def test_default_budget_is_one_percent_and_includes_costs_and_slippage() -> None:
    decision = RiskEngine().evaluate(_opening(), _snapshot())

    assert decision.status == RiskDecisionStatus.APPROVED
    assert decision.budget_reference == Decimal("10.00")
    assert decision.estimated_loss_reference == Decimal("10")


def test_daily_loss_at_three_percent_blocks_open_but_not_reduction() -> None:
    engine = RiskEngine()
    snapshot = _snapshot(daily_pnl=Decimal("-30"))

    opening = engine.evaluate(_opening(), snapshot)
    reduction = engine.evaluate(
        RiskRequest(
            intent_id="REDUCE-1",
            account=ACCOUNT,
            underlying_id="CRUDE-OIL",
            action=RiskAction.REDUCE,
        ),
        snapshot,
    )

    assert RiskRejectionReason.DAILY_LOSS_LIMIT in opening.reasons
    assert reduction.approved is True


def test_unknown_fx_or_exposure_vetoes_opening() -> None:
    engine = RiskEngine()

    missing_fx = engine.evaluate(_opening("FX"), _snapshot(currency="USD"))
    unknown_exposure = engine.evaluate(
        _opening("EXPOSURE"),
        _snapshot(exposure_complete=False),
    )

    assert RiskRejectionReason.FX_INCOMPLETE in missing_fx.reasons
    assert RiskRejectionReason.EXPOSURE_INCOMPLETE in unknown_exposure.reasons


def test_unconfirmed_account_vetoes_opening() -> None:
    snapshot = PortfolioRiskSnapshot(
        reference_currency="EUR",
        accounts=(
            AccountRiskState(
                account=ACCOUNT,
                currency="EUR",
                equity_reference_day=Decimal("1000"),
                equity_current=Decimal("1000"),
                daily_net_pnl=Decimal("0"),
                confirmed=False,
            ),
        ),
    )

    decision = RiskEngine().evaluate(_opening(), snapshot)

    assert decision.reasons == (RiskRejectionReason.ACCOUNT_UNCONFIRMED,)


def test_financial_and_market_vetoes_are_accumulated() -> None:
    request = RiskRequest(
        intent_id="INTENT-VETO",
        account=ACCOUNT,
        underlying_id="CRUDE-OIL",
        action=RiskAction.OPEN,
        estimated_stop_loss=Decimal("11"),
        maximum_ko_loss=Decimal("12"),
        price_fresh=False,
        market_open=False,
        product_supported=False,
    )

    decision = RiskEngine().evaluate(request, _snapshot())

    assert decision.status == RiskDecisionStatus.REJECTED
    assert {
        RiskRejectionReason.STALE_PRICE,
        RiskRejectionReason.MARKET_CLOSED,
        RiskRejectionReason.PRODUCT_UNSUPPORTED,
        RiskRejectionReason.PER_TRADE_LIMIT,
        RiskRejectionReason.KO_LOSS_LIMIT,
    }.issubset(decision.reasons)


def test_global_and_canonical_underlying_limits_include_existing_positions() -> None:
    exposure = ExposureState(
        exposure_id="POSITION-1",
        account=ACCOUNT,
        underlying_id="CRUDE-OIL",
    )
    decision = RiskEngine().evaluate(
        _opening(intent_id="BARRIER-OPEN", underlying="CRUDE-OIL"),
        _snapshot(open_exposures=(exposure,)),
    )

    assert RiskRejectionReason.GLOBAL_EXPOSURE_LIMIT in decision.reasons
    assert RiskRejectionReason.UNDERLYING_EXPOSURE_LIMIT in decision.reasons


def test_concurrent_openings_share_one_atomic_reservation_limit() -> None:
    engine = RiskEngine()
    snapshot = _snapshot()

    with ThreadPoolExecutor(max_workers=2) as executor:
        decisions = list(
            executor.map(
                lambda request: engine.evaluate_and_reserve(request, snapshot),
                (_opening("INTENT-A"), _opening("INTENT-B")),
            )
        )

    assert sum(decision.approved for decision in decisions) == 1
    rejected = next(decision for decision in decisions if not decision.approved)
    assert RiskRejectionReason.GLOBAL_EXPOSURE_LIMIT in rejected.reasons
    assert len(engine.reservations()) == 1


def test_settings_follow_global_account_strategy_market_precedence() -> None:
    settings = resolve_risk_settings(
        global_settings=RiskSettingsLayer(per_trade_fraction=Decimal("0.02")),
        account_settings=RiskSettingsLayer(per_trade_fraction=Decimal("0.015")),
        strategy_settings=RiskSettingsLayer(per_trade_fraction=Decimal("0.012")),
        market_settings=RiskSettingsLayer(per_trade_fraction=Decimal("0.009")),
    )

    assert settings.limits.per_trade_fraction == Decimal("0.009")
    assert settings.source_for("per_trade_fraction") == "market"
