"""Service-health projections that distinguish configuration from observed activity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from trading_ig_assistant.app.projections.common import Availability


@dataclass(frozen=True)
class HealthServiceVM:
    generation_id: int
    service_id: str
    status: Availability
    summary: str
    observed_at_utc: datetime | None = None
    last_success_at_utc: datetime | None = None
    last_error_at_utc: datetime | None = None
    latency_ms: int | None = None
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.generation_id < 0 or not self.service_id.strip() or not self.summary.strip():
            raise ValueError("health projection identity and summary are required")
        for value in (
            self.observed_at_utc,
            self.last_success_at_utc,
            self.last_error_at_utc,
        ):
            if value is not None and (
                value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value)
            ):
                raise ValueError("health timestamps must use UTC")
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
