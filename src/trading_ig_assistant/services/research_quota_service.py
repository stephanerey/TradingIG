"""Conservative monthly credit accounting for external research providers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from typing import Protocol

from trading_ig_assistant.domain.market_intelligence import (
    ResearchQuotaState,
    ResearchQuotaStatus,
    ResearchQuotaView,
    ResearchTrigger,
)


class ResearchQuotaStore(Protocol):
    def load(self) -> ResearchQuotaState | None:
        """Load the last durable quota state."""

    def save(self, state: ResearchQuotaState) -> None:
        """Atomically persist quota state."""


@dataclass(frozen=True)
class ResearchQuotaPolicy:
    planned_budget: int = 704
    hard_limit: int = 900

    def __post_init__(self) -> None:
        if not 0 < self.planned_budget < self.hard_limit:
            raise ValueError("quota policy requires a planned budget below its hard limit")


@dataclass(frozen=True)
class QuotaReservation:
    allowed: bool
    reserved_credits: int
    reason_code: str
    view: ResearchQuotaView


class ResearchQuotaManager:
    """Reserve credits before calls so crashes cannot overspend the quota."""

    def __init__(
        self,
        store: ResearchQuotaStore,
        policy: ResearchQuotaPolicy | None = None,
    ) -> None:
        self._store = store
        self._policy = policy or ResearchQuotaPolicy()
        self._lock = RLock()

    def inspect(self, *, now_utc: datetime) -> ResearchQuotaView:
        _require_utc(now_utc)
        with self._lock:
            state = self._current_state(now_utc)
            return self._view(state, now_utc)

    def reserve(
        self,
        *,
        trigger: ResearchTrigger,
        now_utc: datetime,
        credits: int = 1,
    ) -> QuotaReservation:
        _require_utc(now_utc)
        if credits <= 0:
            raise ValueError("reserved credits must be positive")
        with self._lock:
            state = self._current_state(now_utc)
            limit = (
                self._policy.planned_budget
                if trigger is ResearchTrigger.SCHEDULED
                else self._policy.hard_limit
            )
            if state.used_credits + credits > limit:
                view = self._view(state, now_utc)
                reason = (
                    "TAVILY_PLANNED_BUDGET_REACHED"
                    if limit == self._policy.planned_budget
                    else "TAVILY_MONTHLY_QUOTA_EXHAUSTED"
                )
                return QuotaReservation(False, 0, reason, view)
            updated = _add_usage(state, now_utc, credits)
            self._store.save(updated)
            return QuotaReservation(
                True,
                credits,
                "TAVILY_CREDIT_RESERVED",
                self._view(updated, now_utc),
            )

    def reconcile(
        self,
        *,
        reserved_credits: int,
        actual_credits: int,
        now_utc: datetime,
    ) -> ResearchQuotaView:
        """Reconcile only an explicit provider usage value.

        Unknown failures deliberately keep the reservation and must not call this
        method, preventing accidental reuse of a possibly consumed credit.
        """

        _require_utc(now_utc)
        if reserved_credits < 0 or actual_credits < 0:
            raise ValueError("quota reconciliation credits cannot be negative")
        delta = actual_credits - reserved_credits
        with self._lock:
            state = self._current_state(now_utc)
            updated = _add_usage(state, now_utc, delta)
            if updated.used_credits > self._policy.hard_limit:
                raise ValueError("provider usage exceeds the application hard limit")
            self._store.save(updated)
            return self._view(updated, now_utc)

    def _current_state(self, now_utc: datetime) -> ResearchQuotaState:
        month_key = now_utc.strftime("%Y-%m")
        state = self._store.load()
        if state is None or state.month_key != month_key:
            state = ResearchQuotaState(month_key, 0, ())
            self._store.save(state)
        return state

    def _view(self, state: ResearchQuotaState, now_utc: datetime) -> ResearchQuotaView:
        today = now_utc.strftime("%Y-%m-%d")
        used_today = dict(state.daily_credits).get(today, 0)
        if state.used_credits >= self._policy.hard_limit:
            status = ResearchQuotaStatus.EXHAUSTED
        elif state.used_credits >= self._policy.planned_budget:
            status = ResearchQuotaStatus.RESERVE_ONLY
        else:
            status = ResearchQuotaStatus.AVAILABLE
        return ResearchQuotaView(
            month_key=state.month_key,
            used_credits=state.used_credits,
            used_today=used_today,
            planned_budget=self._policy.planned_budget,
            hard_limit=self._policy.hard_limit,
            remaining_credits=max(0, self._policy.hard_limit - state.used_credits),
            status=status,
        )


def _add_usage(
    state: ResearchQuotaState,
    now_utc: datetime,
    credits: int,
) -> ResearchQuotaState:
    used = state.used_credits + credits
    if used < 0:
        raise ValueError("quota reconciliation exceeds recorded usage")
    day = now_utc.strftime("%Y-%m-%d")
    daily = dict(state.daily_credits)
    daily[day] = daily.get(day, 0) + credits
    if daily[day] < 0:
        raise ValueError("quota reconciliation exceeds recorded daily usage")
    if daily[day] == 0:
        daily.pop(day)
    return ResearchQuotaState(
        month_key=state.month_key,
        used_credits=used,
        daily_credits=tuple(sorted(daily.items())),
    )


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("quota timestamp must use UTC")
