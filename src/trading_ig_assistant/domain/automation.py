"""Immutable, broker-independent contracts for optional AUTO readiness."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256

from trading_ig_assistant.domain.adapter_contracts import AccountRef, OrderIntent


class ExecutionMode(StrEnum):
    ANALYSIS = "analysis"
    SUPERVISED = "supervised"
    AUTO = "auto"
    PAPER = "paper"


class AutomationRejection(StrEnum):
    LIVE_FORBIDDEN = "live_forbidden"
    MODE_NOT_AUTO = "mode_not_auto"
    ACTIVATION_NOT_AUTHORIZED = "activation_not_authorized"
    ACTIVATION_EXPIRED = "activation_expired"
    POLICY_MISMATCH = "policy_mismatch"
    RESTART_REVALIDATION_REQUIRED = "restart_revalidation_required"
    ACCOUNT_NOT_WHITELISTED = "account_not_whitelisted"
    PRODUCT_NOT_WHITELISTED = "product_not_whitelisted"
    STRATEGY_NOT_WHITELISTED = "strategy_not_whitelisted"
    INTENT_EXPIRED = "intent_expired"
    RISK_REJECTED = "risk_rejected"
    CAPABILITY_UNSUPPORTED = "capability_unsupported"
    KILL_SWITCH_ACTIVE = "kill_switch_active"
    RECONCILIATION_INCOMPLETE = "reconciliation_incomplete"
    AMBIGUOUS_EXECUTION_PENDING = "ambiguous_execution_pending"
    SESSION_QUOTA_EXHAUSTED = "session_quota_exhausted"


@dataclass(frozen=True)
class AutomationPolicy:
    policy_id: str
    allowed_account_fingerprints: tuple[str, ...]
    allowed_product_ids: tuple[str, ...]
    allowed_strategy_ids: tuple[str, ...]
    max_intents_per_session: int

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("automation policy ID is required")
        for label, values in (
            ("account", self.allowed_account_fingerprints),
            ("product", self.allowed_product_ids),
            ("strategy", self.allowed_strategy_ids),
        ):
            if any(not value.strip() for value in values):
                raise ValueError(f"automation {label} whitelist contains an empty value")
            if len(set(values)) != len(values):
                raise ValueError(f"automation {label} whitelist contains duplicates")
        if self.max_intents_per_session <= 0:
            raise ValueError("automation session quota must be positive")

    @property
    def digest(self) -> str:
        canonical = json.dumps(
            {
                "policy_id": self.policy_id,
                "allowed_account_fingerprints": sorted(self.allowed_account_fingerprints),
                "allowed_product_ids": sorted(self.allowed_product_ids),
                "allowed_strategy_ids": sorted(self.allowed_strategy_ids),
                "max_intents_per_session": self.max_intents_per_session,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        return sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AutomationActivation:
    activation_id: str
    policy_digest: str
    runtime_generation_id: str
    acceptance_evidence_id: str
    acceptance_evidence_digest: str
    granted_at_utc: datetime
    expires_at_utc: datetime

    def __post_init__(self) -> None:
        required = (
            self.activation_id,
            self.policy_digest,
            self.runtime_generation_id,
            self.acceptance_evidence_id,
        )
        if any(not value.strip() for value in required):
            raise ValueError("automation activation identity fields are required")
        if not _is_sha256(self.policy_digest) or not _is_sha256(self.acceptance_evidence_digest):
            raise ValueError("automation activation digests must be SHA-256 hex values")
        _require_utc(self.granted_at_utc, "activation grant")
        _require_utc(self.expires_at_utc, "activation expiry")
        if self.expires_at_utc <= self.granted_at_utc:
            raise ValueError("automation activation expiry must follow its grant")


@dataclass(frozen=True)
class AutomationRuntimeSnapshot:
    runtime_generation_id: str
    mode: ExecutionMode
    kill_switch_active: bool
    reconciliation_complete: bool
    ambiguous_execution_count: int
    session_intent_count: int
    started_at_utc: datetime

    def __post_init__(self) -> None:
        if not self.runtime_generation_id.strip():
            raise ValueError("automation runtime generation ID is required")
        if self.ambiguous_execution_count < 0 or self.session_intent_count < 0:
            raise ValueError("automation runtime counters must not be negative")
        _require_utc(self.started_at_utc, "runtime start")

    @classmethod
    def safe_start(
        cls,
        runtime_generation_id: str,
        started_at_utc: datetime,
    ) -> AutomationRuntimeSnapshot:
        return cls(
            runtime_generation_id=runtime_generation_id,
            mode=ExecutionMode.ANALYSIS,
            kill_switch_active=True,
            reconciliation_complete=False,
            ambiguous_execution_count=0,
            session_intent_count=0,
            started_at_utc=started_at_utc,
        )


@dataclass(frozen=True)
class AutomationCandidate:
    intent: OrderIntent
    strategy_id: str

    def __post_init__(self) -> None:
        if not self.strategy_id.strip():
            raise ValueError("automation candidate strategy ID is required")


@dataclass(frozen=True)
class AutomationDecision:
    eligible: bool
    policy_id: str
    intent_id: str
    reasons: tuple[AutomationRejection, ...]


def automation_account_fingerprint(account: AccountRef) -> str:
    material = f"{account.broker_id}|{account.environment}|{account.account_id}"
    return sha256(material.encode("utf-8")).hexdigest()


def _require_utc(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"automation {label} must use UTC")


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)
