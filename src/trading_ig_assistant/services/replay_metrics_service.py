"""Deterministic quantitative summaries over closed Paper replay evidence."""

from __future__ import annotations

from decimal import Decimal

from trading_ig_assistant.domain.replay import (
    ReplayExperimentConfig,
    ReplayMetrics,
    ReplayTradeEvidence,
)


def summarize_replay(
    config: ReplayExperimentConfig,
    trades: tuple[ReplayTradeEvidence, ...],
) -> ReplayMetrics:
    _validate_trade_sequence(config, trades)
    pnl_values = tuple(trade.position.realized_pnl or Decimal("0") for trade in trades)
    r_values = tuple(
        pnl / trade.initial_risk_amount for pnl, trade in zip(pnl_values, trades, strict=True)
    )
    trade_count = len(trades)
    wins = sum(value > 0 for value in pnl_values)
    losses = sum(value < 0 for value in pnl_values)
    flats = trade_count - wins - losses
    net_pnl = sum(pnl_values, start=Decimal("0"))
    total_r = sum(r_values, start=Decimal("0"))
    divisor = Decimal(trade_count) if trade_count else Decimal("1")
    return ReplayMetrics(
        config=config,
        trade_count=trade_count,
        win_count=wins,
        loss_count=losses,
        flat_count=flats,
        net_pnl=net_pnl,
        total_r=total_r,
        expectancy_r=total_r / divisor if trade_count else Decimal("0"),
        win_rate=Decimal(wins) / divisor if trade_count else Decimal("0"),
        max_drawdown=_max_drawdown(pnl_values),
        max_drawdown_r=_max_drawdown(r_values),
    )


def compare_replay_modes(results: tuple[ReplayMetrics, ...]) -> tuple[ReplayMetrics, ...]:
    if not results:
        return ()
    baseline = _comparison_key(results[0].config)
    modes: set[str] = set()
    for result in results:
        if _comparison_key(result.config) != baseline:
            raise ValueError("replay comparison requires identical experiment provenance")
        mode = result.config.management_mode
        if mode in modes:
            raise ValueError("replay comparison contains a duplicate management mode")
        modes.add(mode)
    return tuple(sorted(results, key=lambda result: result.config.management_mode))


def _validate_trade_sequence(
    config: ReplayExperimentConfig,
    trades: tuple[ReplayTradeEvidence, ...],
) -> None:
    previous_decision = None
    previous_close = None
    position_ids: set[str] = set()
    for trade in trades:
        position = trade.position
        if position.position_id in position_ids:
            raise ValueError("replay contains a duplicate Paper position")
        position_ids.add(position.position_id)
        if position.currency != config.currency:
            raise ValueError("replay position currency does not match experiment currency")
        if position.fill_model_version != config.fill_model_version:
            raise ValueError("replay fill model does not match experiment provenance")
        if previous_decision is not None and trade.decision_at_utc < previous_decision:
            raise ValueError("replay decisions cannot move backward in time")
        if previous_close is not None and position.closed_at_utc < previous_close:
            raise ValueError("replay closes cannot move backward in time")
        previous_decision = trade.decision_at_utc
        previous_close = position.closed_at_utc


def _max_drawdown(values: tuple[Decimal, ...]) -> Decimal:
    cumulative = Decimal("0")
    peak = Decimal("0")
    maximum = Decimal("0")
    for value in values:
        cumulative += value
        peak = max(peak, cumulative)
        maximum = max(maximum, peak - cumulative)
    return maximum


def _comparison_key(config: ReplayExperimentConfig) -> tuple[object, ...]:
    return (
        config.dataset_id,
        config.dataset_version,
        config.strategy_id,
        config.rules_version,
        config.code_revision,
        config.currency,
        config.fill_model_version,
        config.price_precision,
    )
