from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from inspect import getsource

from trading_ig_assistant.domain.adapter_contracts import (
    AccountRef,
    OrderDirection,
    OrderIntent,
)
from trading_ig_assistant.domain.risk import RiskDecision, RiskDecisionStatus
from trading_ig_assistant.domain.supervised_demo import (
    DemoConfirmationSnapshot,
    DemoGateRejection,
    DemoMutationAuthorization,
    DemoMutationOperation,
    DemoProbePlan,
    DemoProductFamily,
    fingerprint_account,
)
from trading_ig_assistant.services.supervised_demo_gate import SupervisedDemoGate

NOW = datetime(2026, 10, 23, 17, 0, tzinfo=UTC)
ACCOUNT = AccountRef(broker_id="ig", environment="demo", account_id="SYNTHETIC-DEMO")


def _intent(account: AccountRef = ACCOUNT) -> OrderIntent:
    return OrderIntent(
        intent_id="DEMO-PROBE-1",
        account=account,
        product_id="IX.D.SYNTHETIC.IFD.IP",
        underlying_id="US-TECH-100",
        direction=OrderDirection.BUY,
        quantity=Decimal("0.2"),
        requested_stop=None,
        requested_target=None,
        requested_ko=None,
        signal_id=None,
        expires_at_utc=NOW + timedelta(minutes=5),
    )


def _plan() -> DemoProbePlan:
    return DemoProbePlan(
        intent_id="DEMO-PROBE-1",
        account_fingerprint=fingerprint_account(ACCOUNT),
        product_id="IX.D.SYNTHETIC.IFD.IP",
        product_family=DemoProductFamily.CFD,
        direction=OrderDirection.BUY,
        size=Decimal("0.2"),
        expiry="-",
        initial_stop_distance=Decimal("6"),
        tightened_stop_distance=Decimal("4.5"),
        currency="USD",
    )


def _confirmation(plan: DemoProbePlan | None = None) -> DemoConfirmationSnapshot:
    return DemoConfirmationSnapshot(
        plan=plan or _plan(),
        created_at_utc=NOW,
        expires_at_utc=NOW + timedelta(minutes=5),
    )


def _authorization(plan: DemoProbePlan | None = None) -> DemoMutationAuthorization:
    return DemoMutationAuthorization(
        authorization_id="HUMAN-AUTH-20261023",
        plan=plan or _plan(),
        allowed_operations=(
            DemoMutationOperation.CREATE_POSITION,
            DemoMutationOperation.UPDATE_STOP,
            DemoMutationOperation.CLOSE_POSITION,
        ),
        granted_at_utc=NOW,
        expires_at_utc=NOW + timedelta(minutes=10),
    )


def test_exact_demo_probe_is_eligible_without_any_broker_call() -> None:
    decision = SupervisedDemoGate().evaluate_probe(
        intent=_intent(),
        confirmation=_confirmation(),
        authorization=_authorization(),
        risk_decision=RiskDecision(status=RiskDecisionStatus.APPROVED),
        operation=DemoMutationOperation.CREATE_POSITION,
        now_utc=NOW + timedelta(seconds=10),
        kill_switch_active=False,
    )

    assert decision.eligible is True
    assert decision.reasons == ()
    source = getsource(SupervisedDemoGate)
    assert "IGRestAdapter" not in source
    assert ".submit(" not in source


def test_live_scope_is_rejected_even_with_other_valid_inputs() -> None:
    live_account = AccountRef(broker_id="ig", environment="live", account_id="SYNTHETIC-LIVE")
    live_intent = _intent(live_account)

    decision = SupervisedDemoGate().evaluate_probe(
        intent=live_intent,
        confirmation=_confirmation(),
        authorization=_authorization(),
        risk_decision=RiskDecision(status=RiskDecisionStatus.APPROVED),
        operation=DemoMutationOperation.CREATE_POSITION,
        now_utc=NOW,
        kill_switch_active=False,
    )

    assert decision.eligible is False
    assert DemoGateRejection.NOT_DEMO in decision.reasons
    assert DemoGateRejection.PLAN_MISMATCH in decision.reasons


def test_gate_accumulates_expiry_risk_operation_and_kill_switch_vetoes() -> None:
    restricted = replace(
        _authorization(),
        allowed_operations=(DemoMutationOperation.CLOSE_POSITION,),
        expires_at_utc=NOW + timedelta(seconds=1),
    )

    decision = SupervisedDemoGate().evaluate_probe(
        intent=_intent(),
        confirmation=replace(
            _confirmation(),
            expires_at_utc=NOW + timedelta(seconds=1),
        ),
        authorization=restricted,
        risk_decision=RiskDecision(status=RiskDecisionStatus.REJECTED),
        operation=DemoMutationOperation.UPDATE_STOP,
        now_utc=NOW + timedelta(seconds=2),
        kill_switch_active=True,
    )

    assert decision.eligible is False
    assert set(decision.reasons) == {
        DemoGateRejection.CONFIRMATION_EXPIRED,
        DemoGateRejection.AUTHORIZATION_EXPIRED,
        DemoGateRejection.OPERATION_NOT_AUTHORIZED,
        DemoGateRejection.RISK_REJECTED,
        DemoGateRejection.KILL_SWITCH_ACTIVE,
    }
