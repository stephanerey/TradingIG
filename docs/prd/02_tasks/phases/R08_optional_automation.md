# R08 — optional automation

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstruction.

**Last updated:** 2026-10-23

**Status:** IN PROGRESS — OFFLINE READINESS, REPLAY METRICS, CHRONOLOGICAL FEED, GENERIC SIGNAL
ORCHESTRATION AND VALIDATION PLANNING COMPLETE; ACTIVATION NOT AUTHORIZED. R07 completed with
bounded DEMO evidence on 2026-10-23. Exact
whitelist/quota/acceptance choices, validation of an approved strategy on versioned data and an
AUTO activation decision remain absent; all execution stays disabled by default.

**Prerequisite:** [R07](R07_ig_demo_and_supervised_gate.md) completed with actual evidence. [Canonical source sequence and SR boundaries](../../05_coding_agent/sr41_development_workflow.md).

## Goal

Consider optional automation only after quantitative and safety validation.

## Non-goals

No task is launched by reading this specification. No automatic branch switch, dependency installation, broker action or deployment.

## Constraints

Optional and not activated; activating AUTO or real execution requires a distinct explicit
decision. Synthetic replay fixtures are not quantitative strategy acceptance.

## Acceptance criteria

Approved whitelists, deterministic vetoes, kill switch, reconciliation, safe restart and signed acceptance evidence.

## Testing notes

Use phase-appropriate unit/contract/replay or native Windows UI checks from [the acceptance matrix](../../90_quality/acceptance_matrix.md) and [testing strategy](../../90_quality/testing.md). Record actual commands, results and limitations; do not mark acceptance based only on this document.

The generic replay metric core now validates temporal evidence, provenance, net P&L, R and
drawdown offline. Remaining quantitative work requires a separately selected strategy, versioned
dataset and chronological out-of-sample/walk-forward protocol; those choices are not inferred from
the implementation fixtures.

The chronological feed now exposes only closed cumulative candle prefixes from a versioned
in-memory dataset. It is not wired to a selected strategy or execution simulation.

The generic signal orchestrator can invoke an injected strategy with auditable temporal evidence,
but no concrete strategy, scoring pipeline or execution path has been selected or enabled.

Dataset fingerprints and explicit chronological/walk-forward plans are available, but partitions
have not been consumed and no out-of-sample result exists.

## Requirement references

- [Source chapter 7](../../30_feature/F004_market_scanner_and_setup_scoring.md)
- [Source chapter 8](../../30_feature/F006_ticket_builder_and_risk_engine.md)
- [Source chapter 9](../../30_feature/F007_software_pending_orders.md)
- [Source chapter 10](../../30_feature/F008_trade_monitor_and_dynamic_stop_manager.md)
- [Source chapter 14](../../30_feature/F010_backtesting_and_replay.md)
- [Source chapter 16](../../10_architecture/security_and_auth.md)
