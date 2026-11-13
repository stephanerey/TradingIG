from datetime import UTC, datetime, timedelta

import pytest

from trading_ig_assistant.domain.context_sources import ContextCategory
from trading_ig_assistant.domain.market_intelligence import (
    ResearchQuotaState,
    ResearchQuotaStatus,
    ResearchQuotaView,
    ResearchTrigger,
)
from trading_ig_assistant.persistence.research_quota_store import JsonResearchQuotaStore
from trading_ig_assistant.services.market_intelligence_scheduler import (
    IntelligenceSchedule,
    IntelligenceTheme,
    MarketIntelligenceScheduler,
)
from trading_ig_assistant.services.research_quota_service import ResearchQuotaManager

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)


def test_quota_reserves_scheduled_budget_then_preserves_event_reserve(tmp_path) -> None:
    store = JsonResearchQuotaStore(tmp_path / "quota.json")
    store.save(ResearchQuotaState("2026-11", 703, (("2026-11-11", 3),)))
    manager = ResearchQuotaManager(store)

    final_scheduled = manager.reserve(trigger=ResearchTrigger.SCHEDULED, now_utc=NOW)
    assert final_scheduled.allowed
    assert final_scheduled.view.used_credits == 704
    assert final_scheduled.view.status is ResearchQuotaStatus.RESERVE_ONLY

    blocked = manager.reserve(trigger=ResearchTrigger.SCHEDULED, now_utc=NOW)
    assert not blocked.allowed
    assert blocked.reason_code == "TAVILY_PLANNED_BUDGET_REACHED"

    event = manager.reserve(trigger=ResearchTrigger.MARKET_EVENT, now_utc=NOW)
    assert event.allowed
    assert event.view.used_credits == 705


def test_quota_hard_limit_rotation_and_explicit_reconciliation(tmp_path) -> None:
    store = JsonResearchQuotaStore(tmp_path / "quota.json")
    store.save(ResearchQuotaState("2026-11", 900, (("2026-11-11", 900),)))
    manager = ResearchQuotaManager(store)
    blocked = manager.reserve(trigger=ResearchTrigger.MANUAL, now_utc=NOW)
    assert not blocked.allowed
    assert blocked.view.status is ResearchQuotaStatus.EXHAUSTED

    december = datetime(2026, 12, 1, tzinfo=UTC)
    assert manager.inspect(now_utc=december).used_credits == 0
    reservation = manager.reserve(trigger=ResearchTrigger.MANUAL, now_utc=december)
    reconciled = manager.reconcile(
        reserved_credits=reservation.reserved_credits,
        actual_credits=0,
        now_utc=december,
    )
    assert reconciled.used_credits == 0


def test_quota_store_rejects_corrupt_content(tmp_path) -> None:
    path = tmp_path / "quota.json"
    path.write_text("not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="unreadable"):
        JsonResearchQuotaStore(path).load()


def test_scheduler_applies_frequency_cooldown_and_quota_states() -> None:
    scheduler = MarketIntelligenceScheduler(event_cooldown=timedelta(minutes=30))
    quota = ResearchQuotaView("2026-11", 10, 2, 704, 900, 890, ResearchQuotaStatus.AVAILABLE)
    plan = IntelligenceSchedule(
        IntelligenceTheme.ENERGY,
        "energy",
        ContextCategory.ENERGY,
        5,
    )

    cooldown = scheduler.decide(
        trigger=ResearchTrigger.SCHEDULED,
        now_utc=NOW,
        quota=quota,
        schedule=plan,
        last_completed_at_utc=NOW - timedelta(hours=1),
    )
    assert not cooldown.allowed
    assert cooldown.reason_code == "RESEARCH_COOLDOWN_ACTIVE"

    due = scheduler.decide(
        trigger=ResearchTrigger.MARKET_EVENT,
        now_utc=NOW,
        quota=quota,
        last_completed_at_utc=NOW - timedelta(minutes=31),
    )
    assert due.allowed

    reserve_only = ResearchQuotaView(
        "2026-11", 704, 5, 704, 900, 196, ResearchQuotaStatus.RESERVE_ONLY
    )
    blocked = scheduler.decide(
        trigger=ResearchTrigger.SCHEDULED,
        now_utc=NOW,
        quota=reserve_only,
        schedule=plan,
    )
    assert blocked.reason_code == "TAVILY_RESERVE_PRESERVED"
