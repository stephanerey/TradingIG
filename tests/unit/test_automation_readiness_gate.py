from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from inspect import getsource

from trading_ig_assistant.adapters.ig_rest import IGRestAdapter
from trading_ig_assistant.domain.adapter_contracts import (
    AccountRef,
    BrokerCapabilities,
    CapabilitySupport,
    OrderDirection,
    OrderIntent,
)
from trading_ig_assistant.domain.automation import (
    AutomationActivation,
    AutomationCandidate,
    AutomationPolicy,
    AutomationRejection,
    AutomationRuntimeSnapshot,
    ExecutionMode,
    automation_account_fingerprint,
)
from trading_ig_assistant.domain.risk import RiskDecision, RiskDecisionStatus
from trading_ig_assistant.services.automation_readiness_gate import (
    AutomationReadinessGate,
)

NOW = datetime(2026, 10, 23, 20, 0, tzinfo=UTC)
ACCOUNT = AccountRef("ig", "demo", "SYNTHETIC-DEMO")


def _intent(account: AccountRef = ACCOUNT) -> OrderIntent:
    return OrderIntent(
        intent_id="AUTO-INTENT-1",
        account=account,
        product_id="IX.D.SYNTHETIC.IFD.IP",
        underlying_id="SYNTHETIC-INDEX",
        direction=OrderDirection.BUY,
        quantity=Decimal("0.5"),
        requested_stop=Decimal("95"),
        requested_target=Decimal("110"),
        requested_ko=None,
        signal_id="SIGNAL-1",
        expires_at_utc=NOW + timedelta(minutes=5),
    )


def _policy() -> AutomationPolicy:
    return AutomationPolicy(
        policy_id="SYNTHETIC-POLICY",
        allowed_account_fingerprints=(automation_account_fingerprint(ACCOUNT),),
        allowed_product_ids=("IX.D.SYNTHETIC.IFD.IP",),
        allowed_strategy_ids=("SYNTHETIC-STRATEGY",),
        max_intents_per_session=1,
    )


def _activation(
    policy: AutomationPolicy | None = None,
    *,
    generation: str = "RUNTIME-1",
) -> AutomationActivation:
    selected = policy or _policy()
    return AutomationActivation(
        activation_id="SYNTHETIC-ACTIVATION",
        policy_digest=selected.digest,
        runtime_generation_id=generation,
        acceptance_evidence_id="SYNTHETIC-ACCEPTANCE",
        acceptance_evidence_digest=sha256(b"synthetic acceptance").hexdigest(),
        granted_at_utc=NOW,
        expires_at_utc=NOW + timedelta(minutes=10),
    )


def _runtime() -> AutomationRuntimeSnapshot:
    return AutomationRuntimeSnapshot(
        runtime_generation_id="RUNTIME-1",
        mode=ExecutionMode.AUTO,
        kill_switch_active=False,
        reconciliation_complete=True,
        ambiguous_execution_count=0,
        session_intent_count=0,
        started_at_utc=NOW,
    )


def _candidate(account: AccountRef = ACCOUNT) -> AutomationCandidate:
    return AutomationCandidate(intent=_intent(account), strategy_id="SYNTHETIC-STRATEGY")


def _risk(approved: bool = True) -> RiskDecision:
    return RiskDecision(
        status=RiskDecisionStatus.APPROVED if approved else RiskDecisionStatus.REJECTED
    )


def _capabilities(supported: bool = True) -> BrokerCapabilities:
    support = CapabilitySupport.SUPPORTED if supported else CapabilitySupport.UNSUPPORTED
    return BrokerCapabilities(place_orders=support, demo_execution=support)


def _evaluate(**overrides):
    inputs = {
        "candidate": _candidate(),
        "policy": _policy(),
        "activation": _activation(),
        "runtime": _runtime(),
        "risk_decision": _risk(),
        "capabilities": _capabilities(),
        "now_utc": NOW + timedelta(seconds=1),
    }
    inputs.update(overrides)
    return AutomationReadinessGate().evaluate(**inputs)


def test_all_green_synthetic_demo_candidate_is_only_declared_ready() -> None:
    decision = _evaluate()

    assert decision.eligible is True
    assert decision.reasons == ()
    source = getsource(AutomationReadinessGate)
    assert "IGRestAdapter" not in source
    assert ".submit(" not in source
    assert ".create_otc_position(" not in source


def test_safe_start_is_default_deny_without_activation() -> None:
    runtime = AutomationRuntimeSnapshot.safe_start("RUNTIME-1", NOW)

    decision = _evaluate(runtime=runtime, activation=None)

    assert decision.eligible is False
    assert set(decision.reasons) >= {
        AutomationRejection.MODE_NOT_AUTO,
        AutomationRejection.ACTIVATION_NOT_AUTHORIZED,
        AutomationRejection.KILL_SWITCH_ACTIVE,
        AutomationRejection.RECONCILIATION_INCOMPLETE,
    }


def test_live_account_is_forbidden_even_when_every_other_input_is_green() -> None:
    live_account = AccountRef("ig", "live", "SYNTHETIC-LIVE")
    policy = replace(
        _policy(),
        allowed_account_fingerprints=(automation_account_fingerprint(live_account),),
    )

    decision = _evaluate(
        candidate=_candidate(live_account),
        policy=policy,
        activation=_activation(policy),
    )

    assert decision.eligible is False
    assert decision.reasons == (AutomationRejection.LIVE_FORBIDDEN,)


def test_whitelists_risk_and_capabilities_are_independent_vetoes() -> None:
    empty_policy = AutomationPolicy(
        policy_id="EMPTY",
        allowed_account_fingerprints=(),
        allowed_product_ids=(),
        allowed_strategy_ids=(),
        max_intents_per_session=1,
    )

    decision = _evaluate(
        policy=empty_policy,
        activation=_activation(empty_policy),
        risk_decision=_risk(False),
        capabilities=_capabilities(False),
    )

    assert set(decision.reasons) == {
        AutomationRejection.ACCOUNT_NOT_WHITELISTED,
        AutomationRejection.PRODUCT_NOT_WHITELISTED,
        AutomationRejection.STRATEGY_NOT_WHITELISTED,
        AutomationRejection.RISK_REJECTED,
        AutomationRejection.CAPABILITY_UNSUPPORTED,
    }


def test_restart_ambiguity_quota_and_expiry_all_block() -> None:
    restarted = replace(
        _runtime(),
        runtime_generation_id="RUNTIME-2",
        ambiguous_execution_count=1,
        session_intent_count=1,
    )
    expired_intent = replace(
        _intent(),
        expires_at_utc=NOW + timedelta(seconds=1),
    )

    decision = _evaluate(
        candidate=AutomationCandidate(expired_intent, "SYNTHETIC-STRATEGY"),
        runtime=restarted,
        now_utc=NOW + timedelta(seconds=2),
    )

    assert set(decision.reasons) == {
        AutomationRejection.RESTART_REVALIDATION_REQUIRED,
        AutomationRejection.INTENT_EXPIRED,
        AutomationRejection.AMBIGUOUS_EXECUTION_PENDING,
        AutomationRejection.SESSION_QUOTA_EXHAUSTED,
    }


def test_policy_digest_is_order_independent_and_activation_expiry_is_enforced() -> None:
    first = replace(
        _policy(),
        allowed_product_ids=("B", "A"),
        allowed_strategy_ids=("TWO", "ONE"),
    )
    second = replace(
        first,
        allowed_product_ids=("A", "B"),
        allowed_strategy_ids=("ONE", "TWO"),
    )
    activation = replace(
        _activation(first),
        expires_at_utc=NOW + timedelta(seconds=1),
    )

    assert first.digest == second.digest
    decision = _evaluate(
        policy=first,
        activation=activation,
        candidate=AutomationCandidate(_intent(), "ONE"),
        now_utc=NOW + timedelta(seconds=1),
    )
    assert AutomationRejection.ACTIVATION_EXPIRED in decision.reasons


def test_current_ig_adapter_capabilities_keep_auto_blocked() -> None:
    capabilities = IGRestAdapter().capabilities(ACCOUNT, _intent().product_id)

    decision = _evaluate(capabilities=capabilities)

    assert decision.eligible is False
    assert decision.reasons == (AutomationRejection.CAPABILITY_UNSUPPORTED,)


def test_policy_mismatch_is_rejected() -> None:
    changed_policy = replace(_policy(), max_intents_per_session=2)

    decision = _evaluate(policy=changed_policy)

    assert decision.eligible is False
    assert decision.reasons == (AutomationRejection.POLICY_MISMATCH,)
