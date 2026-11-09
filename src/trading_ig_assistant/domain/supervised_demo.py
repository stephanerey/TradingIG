"""Immutable contracts for one explicitly authorized IG DEMO mutation probe."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256

from trading_ig_assistant.domain.adapter_contracts import (
    AccountRef,
    OrderDirection,
    OrderIntent,
)


class DemoMutationOperation(StrEnum):
    CREATE_POSITION = "create_position"
    UPDATE_STOP = "update_stop"
    CLOSE_POSITION = "close_position"


class DemoProductFamily(StrEnum):
    CFD = "cfd"
    BARRIER = "barrier"
    OPTION = "option"


class DemoGateRejection(StrEnum):
    NOT_DEMO = "not_demo"
    ACCOUNT_MISMATCH = "account_mismatch"
    PLAN_MISMATCH = "plan_mismatch"
    CONFIRMATION_EXPIRED = "confirmation_expired"
    AUTHORIZATION_EXPIRED = "authorization_expired"
    OPERATION_NOT_AUTHORIZED = "operation_not_authorized"
    RISK_REJECTED = "risk_rejected"
    KILL_SWITCH_ACTIVE = "kill_switch_active"


@dataclass(frozen=True)
class DemoProbePlan:
    intent_id: str
    account_fingerprint: str
    product_id: str
    product_family: DemoProductFamily
    direction: OrderDirection
    size: Decimal
    expiry: str
    initial_stop_distance: Decimal
    tightened_stop_distance: Decimal
    currency: str

    def __post_init__(self) -> None:
        if not self.intent_id or not self.account_fingerprint or not self.product_id:
            raise ValueError("DEMO probe identifiers are required")
        if self.size <= 0:
            raise ValueError("DEMO probe size must be positive")
        if self.initial_stop_distance <= self.tightened_stop_distance:
            raise ValueError("DEMO probe must tighten the stop")
        if self.tightened_stop_distance <= 0:
            raise ValueError("DEMO stop distance must be positive")
        if len(self.currency) != 3:
            raise ValueError("DEMO probe currency must use three letters")


@dataclass(frozen=True)
class DemoConfirmationSnapshot:
    plan: DemoProbePlan
    created_at_utc: datetime
    expires_at_utc: datetime

    def __post_init__(self) -> None:
        _require_utc(self.created_at_utc, "confirmation creation")
        _require_utc(self.expires_at_utc, "confirmation expiry")
        if self.expires_at_utc <= self.created_at_utc:
            raise ValueError("DEMO confirmation expiry must follow creation")


@dataclass(frozen=True)
class DemoMutationAuthorization:
    authorization_id: str
    plan: DemoProbePlan
    allowed_operations: tuple[DemoMutationOperation, ...]
    granted_at_utc: datetime
    expires_at_utc: datetime

    def __post_init__(self) -> None:
        if not self.authorization_id:
            raise ValueError("DEMO authorization ID is required")
        _require_utc(self.granted_at_utc, "authorization grant")
        _require_utc(self.expires_at_utc, "authorization expiry")
        if self.expires_at_utc <= self.granted_at_utc:
            raise ValueError("DEMO authorization expiry must follow grant")
        if len(set(self.allowed_operations)) != len(self.allowed_operations):
            raise ValueError("DEMO authorization operations must be unique")


@dataclass(frozen=True)
class DemoGateDecision:
    eligible: bool
    authorization_id: str
    intent_id: str
    operation: DemoMutationOperation
    reasons: tuple[DemoGateRejection, ...] = ()


def fingerprint_account(account: AccountRef) -> str:
    material = f"{account.broker_id}|{account.environment}|{account.account_id}"
    return sha256(material.encode("utf-8")).hexdigest()


def plan_matches_intent(plan: DemoProbePlan, intent: OrderIntent) -> bool:
    return (
        plan.intent_id == intent.intent_id
        and plan.account_fingerprint == fingerprint_account(intent.account)
        and plan.product_id == intent.product_id
        and plan.direction is intent.direction
        and plan.size == intent.quantity
    )


def _require_utc(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"DEMO {label} must be timezone-aware")
    if value.utcoffset().total_seconds() != 0:
        raise ValueError(f"DEMO {label} must use UTC")
