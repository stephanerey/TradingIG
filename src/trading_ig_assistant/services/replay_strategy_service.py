"""Generic strategy orchestration over future-blind replay frames."""

from __future__ import annotations

from trading_ig_assistant.domain.analysis import DataState, Strategy
from trading_ig_assistant.domain.replay import (
    ReplayDataset,
    ReplayExperimentConfig,
    ReplaySignalEvidence,
)
from trading_ig_assistant.services.replay_feed_service import build_chronological_frames


def run_strategy_replay(
    config: ReplayExperimentConfig,
    dataset: ReplayDataset,
    strategy: Strategy,
    *,
    required_warmup_points: int = 0,
) -> tuple[ReplaySignalEvidence, ...]:
    if strategy.strategy_id != config.strategy_id:
        raise ValueError("replay strategy does not match experiment provenance")

    frames = build_chronological_frames(
        config,
        dataset,
        required_warmup_points=required_warmup_points,
    )
    evidence_items = []
    previous_decision = None
    signal_ids: set[str] = set()
    for frame in frames:
        signal = strategy.evaluate(frame.indicator_input)
        if signal.strategy_id != config.strategy_id:
            raise ValueError("replay signal strategy does not match experiment provenance")
        if signal.strategy_version != config.rules_version:
            raise ValueError("replay signal version does not match experiment rules")
        if not frame.warmup_complete and signal.data_state is DataState.READY:
            raise ValueError("replay strategy cannot be ready before required warmup")
        if signal.signal_id in signal_ids:
            raise ValueError("replay strategy produced a duplicate signal ID")
        evidence = ReplaySignalEvidence(frame=frame, signal=signal)
        if previous_decision is not None and signal.generated_at_utc < previous_decision:
            raise ValueError("replay signal decisions cannot move backward in time")
        signal_ids.add(signal.signal_id)
        previous_decision = signal.generated_at_utc
        evidence_items.append(evidence)
    return tuple(evidence_items)
