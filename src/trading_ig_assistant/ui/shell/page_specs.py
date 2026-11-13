"""Stable page and subtab identifiers for GUI V2 navigation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageSpec:
    key: str
    title_key: str
    tab_keys: tuple[str, ...]


PAGE_SPECS = (
    PageSpec(
        "dashboard",
        "nav.dashboard",
        ("tab.overview", "tab.performance", "tab.ai_improvement"),
    ),
    PageSpec(
        "scanner",
        "nav.scanner",
        ("tab.catalog", "tab.opportunities", "tab.long", "tab.short", "tab.watch"),
    ),
    PageSpec(
        "watchlist",
        "nav.watchlist",
        ("tab.chart", "tab.technical", "tab.ai_analysis", "tab.trade_plan", "tab.market_history"),
    ),
    PageSpec(
        "positions",
        "nav.positions",
        ("tab.open_positions", "tab.pending", "tab.order_history", "tab.paper", "tab.alerts"),
    ),
    PageSpec(
        "history",
        "nav.history",
        ("tab.trade_journal", "tab.pnl", "tab.statistics", "tab.ai_optimization"),
    ),
    PageSpec(
        "macro",
        "nav.macro",
        ("tab.news", "tab.calendar", "tab.global_context", "tab.ai_snapshots"),
    ),
    PageSpec(
        "diagnostics",
        "nav.diagnostics",
        ("tab.service_health", "tab.flows_quotas", "tab.incidents", "tab.logs"),
    ),
    PageSpec(
        "settings",
        "nav.settings",
        (
            "tab.connections",
            "tab.markets",
            "tab.strategies",
            "tab.risk",
            "tab.ai",
            "tab.notifications",
            "tab.interface",
            "tab.advanced",
        ),
    ),
)

PAGE_SPEC_BY_KEY = {spec.key: spec for spec in PAGE_SPECS}
