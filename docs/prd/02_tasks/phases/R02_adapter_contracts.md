# R02 — adapter contracts

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstruction.

**Last updated:** 2026-10-22

**Status:** COMPLETED on 2026-10-22 with offline contract evidence. No execution capability was activated.

**Prerequisite:** [R01](R01_ohlc_reliability.md) completed with actual evidence. [Canonical source sequence and SR boundaries](../../05_coding_agent/sr41_development_workflow.md).

## Goal

Define broker/data contracts, capabilities and instrument mappings incrementally.

## Non-goals

No task is launched by reading this specification. No automatic branch switch, dependency installation, broker action or deployment.

## Constraints

No mass relocation or replacement of working IG/chart modules.

## Acceptance criteria

Fake-adapter contract tests cover multiple providers and retain existing GUI behavior.

## Testing notes

Use phase-appropriate unit/contract/replay or native Windows UI checks from [the acceptance matrix](../../90_quality/acceptance_matrix.md) and [testing strategy](../../90_quality/testing.md). Record actual commands, results and limitations; do not mark acceptance based only on this document.

## Requirement references

- [Source chapter 4](../../10_architecture/overview.md)
- [Source chapter 17](../../10_architecture/domain_contracts.md)
