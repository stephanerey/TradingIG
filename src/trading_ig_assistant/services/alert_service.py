"""In-memory alert inbox with deterministic cooldown and acknowledgement."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from threading import Lock

from trading_ig_assistant.domain.alerts import AlertCategory, AlertSeverity, LocalAlert


class LocalAlertService:
    def __init__(self, cooldown: timedelta = timedelta(0)) -> None:
        if cooldown < timedelta(0):
            raise ValueError("alert cooldown must not be negative")
        self._cooldown = cooldown
        self._alerts: dict[str, LocalAlert] = {}
        self._last_by_key: dict[tuple[AlertCategory, str], datetime] = {}
        self._sequence = 0
        self._lock = Lock()

    def publish(
        self,
        *,
        category: AlertCategory,
        severity: AlertSeverity,
        message: str,
        correlation_id: str,
        timestamp_utc: datetime,
    ) -> LocalAlert | None:
        key = (category, correlation_id)
        with self._lock:
            previous = self._last_by_key.get(key)
            if previous is not None and timestamp_utc < previous:
                raise ValueError("alert timestamps cannot move backward for one correlation")
            if previous is not None and timestamp_utc - previous < self._cooldown:
                return None
            self._sequence += 1
            alert = LocalAlert(
                alert_id=f"LOCAL-ALERT-{self._sequence}",
                category=category,
                severity=severity,
                message=message,
                created_at_utc=timestamp_utc,
                correlation_id=correlation_id,
            )
            self._alerts[alert.alert_id] = alert
            self._last_by_key[key] = timestamp_utc
            return alert

    def acknowledge(self, alert_id: str) -> LocalAlert:
        with self._lock:
            updated = replace(self._alerts[alert_id], acknowledged=True)
            self._alerts[alert_id] = updated
            return updated

    def alerts(self) -> tuple[LocalAlert, ...]:
        with self._lock:
            return tuple(self._alerts.values())
