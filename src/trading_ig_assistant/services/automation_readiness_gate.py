"""Pure default-deny evaluator for optional AUTO readiness."""

from __future__ import annotations

from datetime import datetime

from trading_ig_assistant.domain.adapter_contracts import (
    BrokerCapabilities,
    CapabilitySupport,
)
from trading_ig_assistant.domain.automation import (
    AutomationActivation,
    AutomationCandidate,
    AutomationDecision,
    AutomationPolicy,
    AutomationRejection,
    AutomationRuntimeSnapshot,
    ExecutionMode,
    automation_account_fingerprint,
)
from trading_ig_assistant.domain.risk import RiskDecision


class AutomationReadinessGate:
    """Evaluate readiness only; this service has no broker or execution dependency."""

    def evaluate(
        self,
        *,
        candidate: AutomationCandidate,
        policy: AutomationPolicy,
        activation: AutomationActivation | None,
        runtime: AutomationRuntimeSnapshot,
        risk_decision: RiskDecision,
        capabilities: BrokerCapabilities,
        now_utc: datetime,
    ) -> AutomationDecision:
        if now_utc.tzinfo is None or now_utc.utcoffset() is None:
            raise ValueError("automation evaluation time must be timezone-aware")
        reasons: list[AutomationRejection] = []
        account = candidate.intent.account
        if account.broker_id != "ig" or account.environment != "demo":
            reasons.append(AutomationRejection.LIVE_FORBIDDEN)
        if runtime.mode is not ExecutionMode.AUTO:
            reasons.append(AutomationRejection.MODE_NOT_AUTO)
        if activation is None:
            reasons.append(AutomationRejection.ACTIVATION_NOT_AUTHORIZED)
        else:
            if now_utc >= activation.expires_at_utc:
                reasons.append(AutomationRejection.ACTIVATION_EXPIRED)
            if activation.policy_digest != policy.digest:
                reasons.append(AutomationRejection.POLICY_MISMATCH)
            if activation.runtime_generation_id != runtime.runtime_generation_id:
                reasons.append(AutomationRejection.RESTART_REVALIDATION_REQUIRED)
        if automation_account_fingerprint(account) not in policy.allowed_account_fingerprints:
            reasons.append(AutomationRejection.ACCOUNT_NOT_WHITELISTED)
        if candidate.intent.product_id not in policy.allowed_product_ids:
            reasons.append(AutomationRejection.PRODUCT_NOT_WHITELISTED)
        if candidate.strategy_id not in policy.allowed_strategy_ids:
            reasons.append(AutomationRejection.STRATEGY_NOT_WHITELISTED)
        if now_utc >= candidate.intent.expires_at_utc:
            reasons.append(AutomationRejection.INTENT_EXPIRED)
        if not risk_decision.approved:
            reasons.append(AutomationRejection.RISK_REJECTED)
        if not (
            capabilities.place_orders is CapabilitySupport.SUPPORTED
            and capabilities.demo_execution is CapabilitySupport.SUPPORTED
        ):
            reasons.append(AutomationRejection.CAPABILITY_UNSUPPORTED)
        if runtime.kill_switch_active:
            reasons.append(AutomationRejection.KILL_SWITCH_ACTIVE)
        if not runtime.reconciliation_complete:
            reasons.append(AutomationRejection.RECONCILIATION_INCOMPLETE)
        if runtime.ambiguous_execution_count:
            reasons.append(AutomationRejection.AMBIGUOUS_EXECUTION_PENDING)
        if runtime.session_intent_count >= policy.max_intents_per_session:
            reasons.append(AutomationRejection.SESSION_QUOTA_EXHAUSTED)
        return AutomationDecision(
            eligible=not reasons,
            policy_id=policy.policy_id,
            intent_id=candidate.intent.intent_id,
            reasons=tuple(dict.fromkeys(reasons)),
        )
