# R01 — ohlc reliability

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstruction.

**Last updated:** 2026-10-22

**Status:** COMPLETED on 2026-10-22 with cache, aggregation and Qt responsiveness regressions.

**Prerequisite:** [R00](R00_baseline.md) completed with actual evidence. [Canonical source sequence and SR boundaries](../../05_coding_agent/sr41_development_workflow.md).

## Goal

Address source-reported quota/cache, M1 aggregation and blocking GUI I/O defects only after reproduction.

## Non-goals

No task is launched by reading this specification. No automatic branch switch, dependency installation, broker action or deployment.

## Constraints

Compaction and account persistence are later findings unless evidence justifies a scoped fix.

## Acceptance criteria

Cache remains readable at exhausted quota; five M1 candles aggregate correctly including revisions; slow fake history provider does not block Qt.

## Testing notes

Use phase-appropriate unit/contract/replay or native Windows UI checks from [the acceptance matrix](../../90_quality/acceptance_matrix.md) and [testing strategy](../../90_quality/testing.md). Record actual commands, results and limitations; do not mark acceptance based only on this document.

## Requirement references

- [Source chapter 6](../../30_feature/F003_realtime_market_data_and_charts.md)
- [Source chapter 18](../../05_coding_agent/sr41_development_workflow.md)
- [Source chapter 19](../../90_quality/acceptance_matrix.md)
