"""Immutable read models exposed to GUI V2."""

from trading_ig_assistant.app.projections.account import AccountHeaderVM
from trading_ig_assistant.app.projections.account_projection import (
    build_account_header_projection,
    build_runtime_health_projection,
)
from trading_ig_assistant.app.projections.common import Amount, Availability, DataProvenance
from trading_ig_assistant.app.projections.dashboard import (
    DashboardVM,
    PositionRowVM,
    RealizedPnlVM,
)
from trading_ig_assistant.app.projections.dashboard_projection import (
    build_paper_dashboard_projection,
)
from trading_ig_assistant.app.projections.health import HealthServiceVM
from trading_ig_assistant.app.projections.scanner import ScannerMarketRowVM, ScannerVM

__all__ = [
    "AccountHeaderVM",
    "Amount",
    "Availability",
    "DataProvenance",
    "HealthServiceVM",
    "build_account_header_projection",
    "build_runtime_health_projection",
    "DashboardVM",
    "PositionRowVM",
    "RealizedPnlVM",
    "build_paper_dashboard_projection",
    "ScannerMarketRowVM",
    "ScannerVM",
]
