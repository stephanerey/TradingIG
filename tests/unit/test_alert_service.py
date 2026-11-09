from datetime import UTC, datetime, timedelta

import pytest

from trading_ig_assistant.domain.alerts import AlertCategory, AlertSeverity
from trading_ig_assistant.services.alert_service import LocalAlertService

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)


def test_local_alerts_apply_cooldown_and_remain_acknowledgeable() -> None:
    service = LocalAlertService(cooldown=timedelta(minutes=1))

    first = service.publish(
        category=AlertCategory.PENDING_TRIGGERED,
        severity=AlertSeverity.WARNING,
        message="Paper pending triggered",
        correlation_id="PENDING-1",
        timestamp_utc=NOW,
    )
    duplicate = service.publish(
        category=AlertCategory.PENDING_TRIGGERED,
        severity=AlertSeverity.WARNING,
        message="Paper pending triggered again",
        correlation_id="PENDING-1",
        timestamp_utc=NOW + timedelta(seconds=30),
    )

    assert first is not None
    assert duplicate is None
    acknowledged = service.acknowledge(first.alert_id)
    assert acknowledged.acknowledged is True
    assert len(service.alerts()) == 1

    with pytest.raises(ValueError, match="backward"):
        service.publish(
            category=AlertCategory.PENDING_TRIGGERED,
            severity=AlertSeverity.WARNING,
            message="Older alert",
            correlation_id="PENDING-1",
            timestamp_utc=NOW - timedelta(seconds=1),
        )
