from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.adapter_contracts import AccountRef, OrderDirection
from trading_ig_assistant.domain.positions import (
    PaperExitReason,
    PaperPosition,
    PaperPositionStatus,
)
from trading_ig_assistant.domain.replay import (
    ReplayExperimentConfig,
    ReplayPricePrecision,
    ReplayTradeEvidence,
)
from trading_ig_assistant.services.replay_metrics_service import (
    compare_replay_modes,
    summarize_replay,
)

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
ACCOUNT = AccountRef("paper", "paper", "SYNTHETIC-PAPER")


def _config(mode: str = "fixed_target") -> ReplayExperimentConfig:
    return ReplayExperimentConfig(
        experiment_id=f"SYNTHETIC-{mode}",
        dataset_id="SYNTHETIC-DATASET",
        dataset_version="fixture-v1",
        strategy_id="SYNTHETIC-STRATEGY",
        rules_version="rules-v1",
        code_revision="synthetic-revision",
        management_mode=mode,
        currency="EUR",
        fill_model_version="paper-fill-v1",
        price_precision=ReplayPricePrecision.BID_ASK,
    )


def _position(index: int, pnl: str) -> PaperPosition:
    opened = NOW + timedelta(minutes=index * 10)
    return PaperPosition(
        position_id=f"PAPER-{index}",
        intent_id=f"INTENT-{index}",
        account=ACCOUNT,
        product_id="SYNTHETIC-PRODUCT",
        underlying_id="SYNTHETIC-UNDERLYING",
        direction=OrderDirection.BUY,
        quantity=Decimal("1"),
        entry_price=Decimal("100"),
        current_stop=Decimal("90"),
        target=Decimal("110"),
        knockout=None,
        opened_at_utc=opened,
        opening_fee=Decimal("0.5"),
        entry_slippage=Decimal("0.25"),
        currency="EUR",
        price_provenance="fixture:bid-ask",
        fill_model_version="paper-fill-v1",
        status=PaperPositionStatus.CLOSED,
        closed_at_utc=opened + timedelta(minutes=5),
        close_price=Decimal("100") + Decimal(pnl),
        closing_fee=Decimal("0.5"),
        realized_pnl=Decimal(pnl),
        exit_reason=PaperExitReason.MANUAL,
    )


def _evidence(index: int, pnl: str, risk: str = "10") -> ReplayTradeEvidence:
    position = _position(index, pnl)
    return ReplayTradeEvidence(
        position=position,
        latest_source_at_utc=position.opened_at_utc - timedelta(seconds=1),
        decision_at_utc=position.opened_at_utc,
        initial_risk_amount=Decimal(risk),
    )


def test_summary_uses_net_pnl_and_reports_r_drawdown_and_expectancy() -> None:
    metrics = summarize_replay(
        _config(),
        (_evidence(0, "10"), _evidence(1, "-5")),
    )

    assert metrics.trade_count == 2
    assert metrics.win_count == 1
    assert metrics.loss_count == 1
    assert metrics.flat_count == 0
    assert metrics.net_pnl == Decimal("5")
    assert metrics.total_r == Decimal("0.5")
    assert metrics.expectancy_r == Decimal("0.25")
    assert metrics.win_rate == Decimal("0.5")
    assert metrics.max_drawdown == Decimal("5")
    assert metrics.max_drawdown_r == Decimal("0.5")


def test_empty_replay_is_explicitly_zero_not_profitable() -> None:
    metrics = summarize_replay(_config(), ())

    assert metrics.trade_count == 0
    assert metrics.net_pnl == Decimal("0")
    assert metrics.total_r == Decimal("0")
    assert metrics.expectancy_r == Decimal("0")
    assert metrics.win_rate == Decimal("0")


def test_source_newer_than_decision_is_rejected_as_look_ahead() -> None:
    trade = _evidence(0, "10")

    with pytest.raises(ValueError, match="look-ahead"):
        replace(
            trade,
            latest_source_at_utc=trade.decision_at_utc + timedelta(seconds=1),
        )


def test_open_position_and_reverse_time_are_rejected() -> None:
    closed = _position(0, "10")
    open_position = replace(
        closed,
        status=PaperPositionStatus.OPEN,
        closed_at_utc=None,
        close_price=None,
        closing_fee=None,
        realized_pnl=None,
        exit_reason=None,
    )
    with pytest.raises(ValueError, match="closed Paper position"):
        ReplayTradeEvidence(
            open_position,
            latest_source_at_utc=NOW,
            decision_at_utc=NOW,
            initial_risk_amount=Decimal("10"),
        )

    with pytest.raises(ValueError, match="decision cannot follow"):
        ReplayTradeEvidence(
            closed,
            latest_source_at_utc=closed.opened_at_utc,
            decision_at_utc=closed.opened_at_utc + timedelta(seconds=1),
            initial_risk_amount=Decimal("10"),
        )


def test_sequence_rejects_duplicates_backward_closes_and_mixed_provenance() -> None:
    first = _evidence(0, "10")
    second = _evidence(1, "-5")

    with pytest.raises(ValueError, match="duplicate"):
        summarize_replay(_config(), (first, first))
    with pytest.raises(ValueError, match="decisions cannot move backward"):
        summarize_replay(_config(), (second, first))
    with pytest.raises(ValueError, match="currency"):
        summarize_replay(
            _config(),
            (replace(first, position=replace(first.position, currency="USD")),),
        )
    with pytest.raises(ValueError, match="fill model"):
        summarize_replay(
            _config(),
            (replace(first, position=replace(first.position, fill_model_version="other")),),
        )

    later_close = replace(
        first,
        position=replace(
            first.position,
            closed_at_utc=second.position.closed_at_utc + timedelta(minutes=5),
        ),
    )
    with pytest.raises(ValueError, match="closes cannot move backward"):
        summarize_replay(_config(), (later_close, second))


def test_mode_comparison_requires_same_provenance_and_unique_modes() -> None:
    fixed = summarize_replay(_config("fixed_target"), (_evidence(0, "10"),))
    trailing = summarize_replay(_config("trailing"), (_evidence(0, "12"),))

    comparison = compare_replay_modes((trailing, fixed))

    assert [result.config.management_mode for result in comparison] == [
        "fixed_target",
        "trailing",
    ]
    with pytest.raises(ValueError, match="duplicate management mode"):
        compare_replay_modes((fixed, fixed))
    with pytest.raises(ValueError, match="identical experiment provenance"):
        compare_replay_modes(
            (
                fixed,
                replace(
                    trailing,
                    config=replace(trailing.config, dataset_version="fixture-v2"),
                ),
            )
        )
