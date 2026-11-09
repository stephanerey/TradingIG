"""Local alert models; no external delivery contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertCategory(StrEnum):
    PENDING_TRIGGERED = "pending_triggered"
    ORDER_RESULT = "order_result"
    STOP_UPDATE = "stop_update"
    SAFE_DEGRADATION = "safe_degradation"


@dataclass(frozen=True)
class LocalAlert:
    alert_id: str
    category: AlertCategory
    severity: AlertSeverity
    message: str
    created_at_utc: datetime
    correlation_id: str
    acknowledged: bool = False

    def __post_init__(self) -> None:
        if not self.alert_id.strip() or not self.message.strip() or not self.correlation_id.strip():
            raise ValueError("alert id, message and correlation id are required")
        if self.created_at_utc.tzinfo is None or self.created_at_utc.utcoffset() != UTC.utcoffset(
            self.created_at_utc
        ):
            raise ValueError("alert timestamp must use UTC")
