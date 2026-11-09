# R07 — ig demo and supervised gate

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstruction.

**Last updated:** 2026-10-23

**Status:** COMPLETE WITH EXPLICIT UNSUPPORTED CAPABILITIES. Authenticated DEMO read access,
accounts, positions, working orders, bounded activity, market metadata and representative `PRICE`
streaming are validated. One separately authorized minimum-size CFD create/confirm/stop-update/close
probe completed with final zero open positions. Barrière, Option, working-order and LIVE execution
remain `UNSUPPORTED`; general broker execution is not activated.

**Prerequisite:** [R06](R06_paper_and_trade_manager.md) completed with actual evidence. [Canonical source sequence and SR boundaries](../../05_coding_agent/sr41_development_workflow.md).

## Goal

Collect IG CFD/Barriers/Options capability evidence and validate demo/supervised execution gates.

## Non-goals

No task is launched by reading this specification. No automatic branch switch, dependency installation, broker action or deployment.

## Constraints

This phase document does not authorize real-account actions. Source §9 demands specific authorization for any later real capability test.

## Acceptance criteria

Sanitized demo evidence, explicit account checks, timeout reconciliation and capability matrix.

## Testing notes

Use phase-appropriate unit/contract/replay or native Windows UI checks from [the acceptance matrix](../../90_quality/acceptance_matrix.md) and [testing strategy](../../90_quality/testing.md). Record actual commands, results and limitations; do not mark acceptance based only on this document.

## Requirement references

- [Source chapter 5](../../30_feature/F001_ig_connection_and_settings.md)
- [Source chapter 8](../../30_feature/F006_ticket_builder_and_risk_engine.md)
- [Source chapter 9](../../30_feature/F007_software_pending_orders.md)
- [Source chapter 20](../../01_product/risks_and_assumptions.md)
