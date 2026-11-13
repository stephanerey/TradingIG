"""Build a conservative local optimization-readiness assessment."""

from __future__ import annotations

from datetime import datetime

from trading_ig_assistant.app.projections.optimization import (
    OptimizationReviewStatus,
    OptimizationReviewVM,
)
from trading_ig_assistant.domain.journal import JournalEvent, PnlStatus


def build_optimization_review(
    *,
    generation_id: int,
    events: tuple[JournalEvent, ...],
    generated_at_utc: datetime,
) -> OptimizationReviewVM:
    """Assess evidence without calling AI or manufacturing recommendations.

    The current Paper journal does not yet attest strategy/parameter versions or a
    versioned replay dataset. Consequently even a large sample remains unsuitable
    for a governed proposal. This explicit result prevents performance KPIs from
    being mistaken for optimization evidence.
    """

    closures = tuple(
        sorted(
            (
                event
                for event in events
                if event.event_type == "PAPER_POSITION_CLOSED"
                and event.pnl_status is PnlStatus.REALIZED
                and event.pnl_amount is not None
                and event.pnl_currency is not None
            ),
            key=lambda event: event.timestamp_utc,
        )
    )
    reasons: list[str] = []
    if not closures:
        reasons.append("NO_ATTESTED_CLOSED_TRADES")
    elif len(closures) < 30:
        reasons.append("SAMPLE_SIZE_EXPLORATORY")
    if len({event.pnl_currency.upper() for event in closures if event.pnl_currency}) > 1:
        reasons.append("MULTI_CURRENCY_REQUIRES_SEPARATE_SCOPES")
    reasons.extend(
        (
            "DATASET_NOT_VERSIONED",
            "STRATEGY_VERSION_UNAVAILABLE",
            "PARAMETER_VERSION_UNAVAILABLE",
            "OUT_OF_SAMPLE_REPLAY_NOT_RUN",
            "EXTERNAL_AI_NOT_AUTHORIZED",
        )
    )
    return OptimizationReviewVM(
        generation_id=generation_id,
        generated_at_utc=generated_at_utc,
        scope="paper:local-paper-preview:closed-trades",
        execution_mode="PAPER",
        trade_count=len(closures),
        currencies=tuple(
            sorted({event.pnl_currency.upper() for event in closures if event.pnl_currency})
        ),
        first_trade_at_utc=closures[0].timestamp_utc if closures else None,
        last_trade_at_utc=closures[-1].timestamp_utc if closures else None,
        dataset_version=None,
        status=OptimizationReviewStatus.INSUFFICIENT_EVIDENCE,
        reason_codes=tuple(reasons),
        external_ai_authorized=False,
        proposals=(),
    )
