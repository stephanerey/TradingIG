# F007 — Software Pending Orders

> **PRD Policy:** **PROJECT (editable)** — Feature specification.  
**Last updated:** 2026-05-07


## Goal
Implement app-managed delayed entry conditions for Barriers/Options when native IG delayed-order workflow is unavailable, unsuitable, or disabled.

## Non-goals
- MVP does not blindly execute live orders on trigger.
- MVP does not rely on a single tick crossing a level without confirmation.

## Requirements
- Revalidate `MacroRibbonState` at trigger time. A pending order armed during green conditions may be downgraded, paused, or require confirmation if the ribbon turns red/yellow before trigger.
- Pending order states: `DRAFT`, `ARMED`, `TRIGGERED`, `CONFIRMED`, `EXECUTED`, `CANCELLED`, `EXPIRED`, `FAILED`.
- Trigger types:
  - price crosses above/below level;
  - price touches zone;
  - breakout + hold time;
  - candle close above/below level;
  - pullback to zone + rebound confirmation.
- Parameters: instrument/product, direction, trigger level/zone, tolerance, max acceptable slippage, expiry time, confirmation rule, ticket template.
- On trigger, revalidate data freshness, spread, market status, product status, KO distance, R/R, total exposure.
- Alert user and show prepared ticket for manual confirmation.
- Log all state changes.

## Constraints
- Must avoid repeated triggers around the same level via cooldown and state locking.
- Must disable triggers when streaming data is stale.
- Must not open a trade if ticket is invalid at trigger time.

## Acceptance criteria
- A replay test triggers exactly once on a valid breakout.
- A wick without confirmation does not trigger when candle-close confirmation is configured.
- Expired pending orders do not trigger.

## Testing notes
- Replay candle/tick sequences.
- Unit-test state transitions and validation gates.
