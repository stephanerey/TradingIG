"""Pure scheduling decisions for bounded market-intelligence searches."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from trading_ig_assistant.domain.context_sources import ContextCategory
from trading_ig_assistant.domain.market_intelligence import (
    ResearchQuotaStatus,
    ResearchQuotaView,
    ResearchTrigger,
)


class IntelligenceTheme(StrEnum):
    ENERGY = "energy"
    PRECIOUS_METALS = "precious_metals"
    US_EQUITIES = "us_equities"
    EUROPEAN_EQUITIES = "european_equities"
    US_MACRO = "us_macro"
    GLOBAL_GEOPOLITICS = "global_geopolitics"


@dataclass(frozen=True)
class IntelligenceSchedule:
    theme: IntelligenceTheme
    query: str
    category: ContextCategory
    searches_per_market_day: int

    def __post_init__(self) -> None:
        if not self.query.strip() or not 1 <= self.searches_per_market_day <= 5:
            raise ValueError("intelligence schedule query and bounded frequency are required")

    @property
    def minimum_interval(self) -> timedelta:
        return timedelta(hours=24 / self.searches_per_market_day)


@dataclass(frozen=True)
class IntelligenceFreshnessPolicy:
    """Configurable discovery windows by evidence family."""

    breaking_news: timedelta = timedelta(hours=6)
    macroeconomics: timedelta = timedelta(hours=24)
    monetary_policy: timedelta = timedelta(hours=72)
    geopolitics: timedelta = timedelta(days=7)

    def __post_init__(self) -> None:
        if min(
            self.breaking_news,
            self.macroeconomics,
            self.monetary_policy,
            self.geopolitics,
        ) < timedelta(minutes=15):
            raise ValueError("intelligence freshness windows must be at least 15 minutes")

    def for_category(self, category: ContextCategory) -> timedelta:
        if category in {
            ContextCategory.INFLATION,
            ContextCategory.EMPLOYMENT,
            ContextCategory.GROWTH,
        }:
            return self.macroeconomics
        if category in {ContextCategory.CENTRAL_BANK, ContextCategory.RATES}:
            return self.monetary_policy
        if category is ContextCategory.GEOPOLITICAL:
            return self.geopolitics
        return self.breaking_news


@dataclass(frozen=True)
class SchedulerDecision:
    allowed: bool
    reason_code: str
    next_eligible_at_utc: datetime | None


DEFAULT_INTELLIGENCE_SCHEDULES = (
    IntelligenceSchedule(
        IntelligenceTheme.ENERGY,
        "oil OR natural gas OR OPEC OR energy supply disruption",
        ContextCategory.ENERGY,
        5,
    ),
    IntelligenceSchedule(
        IntelligenceTheme.PRECIOUS_METALS,
        "gold OR precious metals OR real yields OR central bank gold",
        ContextCategory.RATES,
        5,
    ),
    IntelligenceSchedule(
        IntelligenceTheme.US_EQUITIES,
        "US equities OR Nasdaq OR S&P 500 market news",
        ContextCategory.OTHER,
        5,
    ),
    IntelligenceSchedule(
        IntelligenceTheme.EUROPEAN_EQUITIES,
        "European equities OR DAX OR CAC 40 market news",
        ContextCategory.OTHER,
        5,
    ),
    IntelligenceSchedule(
        IntelligenceTheme.US_MACRO,
        "Federal Reserve OR US inflation OR US employment OR US GDP",
        ContextCategory.OTHER,
        2,
    ),
    IntelligenceSchedule(
        IntelligenceTheme.GLOBAL_GEOPOLITICS,
        "geopolitical crisis OR sanctions OR conflict OR trade restrictions",
        ContextCategory.GEOPOLITICAL,
        2,
    ),
)


class MarketIntelligenceScheduler:
    def __init__(self, *, event_cooldown: timedelta = timedelta(minutes=30)) -> None:
        if event_cooldown <= timedelta(0):
            raise ValueError("event research cooldown must be positive")
        self._event_cooldown = event_cooldown

    def decide(
        self,
        *,
        trigger: ResearchTrigger,
        now_utc: datetime,
        quota: ResearchQuotaView,
        schedule: IntelligenceSchedule | None = None,
        last_completed_at_utc: datetime | None = None,
    ) -> SchedulerDecision:
        _require_utc(now_utc)
        if last_completed_at_utc is not None:
            _require_utc(last_completed_at_utc)
            if last_completed_at_utc > now_utc:
                raise ValueError("scheduler history cannot be future-dated")
        if quota.status is ResearchQuotaStatus.EXHAUSTED:
            return SchedulerDecision(False, "TAVILY_MONTHLY_QUOTA_EXHAUSTED", None)
        if trigger is ResearchTrigger.SCHEDULED:
            if schedule is None:
                raise ValueError("scheduled research requires a schedule")
            if quota.status is ResearchQuotaStatus.RESERVE_ONLY:
                return SchedulerDecision(False, "TAVILY_RESERVE_PRESERVED", None)
            interval = schedule.minimum_interval
        elif trigger in {ResearchTrigger.MARKET_EVENT, ResearchTrigger.MACRO_EVENT}:
            interval = self._event_cooldown
        else:
            interval = timedelta(0)
        if last_completed_at_utc is not None:
            eligible_at = last_completed_at_utc + interval
            if now_utc < eligible_at:
                return SchedulerDecision(False, "RESEARCH_COOLDOWN_ACTIVE", eligible_at)
        return SchedulerDecision(True, "RESEARCH_DUE", now_utc)


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("scheduler timestamp must use UTC")
