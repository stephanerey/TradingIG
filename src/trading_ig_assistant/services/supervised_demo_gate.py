"""Pure decision gate for a bounded IG DEMO probe; it has no broker call path."""

from __future__ import annotations

from datetime import datetime

from trading_ig_assistant.domain.adapter_contracts import OrderIntent
from trading_ig_assistant.domain.risk import RiskDecision
from trading_ig_assistant.domain.supervised_demo import (
    DemoConfirmationSnapshot,
    DemoGateDecision,
    DemoGateRejection,
    DemoMutationAuthorization,
    DemoMutationOperation,
    plan_matches_intent,
)


class SupervisedDemoGate:
    """Evaluate eligibility only; this service cannot submit, amend or close a position."""

    def evaluate_probe(
        self,
        *,
        intent: OrderIntent,
        confirmation: DemoConfirmationSnapshot,
        authorization: DemoMutationAuthorization,
        risk_decision: RiskDecision,
        operation: DemoMutationOperation,
        now_utc: datetime,
        kill_switch_active: bool,
    ) -> DemoGateDecision:
        reasons: list[DemoGateRejection] = []
        if intent.account.broker_id != "ig" or intent.account.environment != "demo":
            reasons.append(DemoGateRejection.NOT_DEMO)
        if not plan_matches_intent(confirmation.plan, intent):
            reasons.append(DemoGateRejection.PLAN_MISMATCH)
        if authorization.plan != confirmation.plan:
            reasons.append(DemoGateRejection.ACCOUNT_MISMATCH)
        if now_utc > confirmation.expires_at_utc:
            reasons.append(DemoGateRejection.CONFIRMATION_EXPIRED)
        if now_utc > authorization.expires_at_utc:
            reasons.append(DemoGateRejection.AUTHORIZATION_EXPIRED)
        if operation not in authorization.allowed_operations:
            reasons.append(DemoGateRejection.OPERATION_NOT_AUTHORIZED)
        if not risk_decision.approved:
            reasons.append(DemoGateRejection.RISK_REJECTED)
        if kill_switch_active:
            reasons.append(DemoGateRejection.KILL_SWITCH_ACTIVE)
        return DemoGateDecision(
            eligible=not reasons,
            authorization_id=authorization.authorization_id,
            intent_id=intent.intent_id,
            operation=operation,
            reasons=tuple(reasons),
        )
