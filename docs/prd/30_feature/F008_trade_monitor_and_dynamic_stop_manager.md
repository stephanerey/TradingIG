# F008 — Trade Monitor and Dynamic Stop Manager

> **PRD Policy:** **PROJECT (editable)** — Feature specification.  
**Last updated:** 2026-05-07


## Goal
Monitor open trades and manage stop updates using deterministic R-based state-machine rules.

## Non-goals
- No discretionary stop changes by hidden logic.
- No widening stop after entry.

## Requirements
- Trade states: `OPEN`, `PROTECTED`, `TRAILING`, `CLOSING`, `CLOSED`.
- Calculate initial risk `R` from entry and initial stop.
- At configured threshold, move stop to break-even + costs if supported or recommend this action.
- At later thresholds, trail stop by one of configurable modes:
  - fixed R lock-in;
  - recent candle lows/highs;
  - ATR/volatility;
  - manual level.
- Never move a long stop downward or a short stop upward.
- Allow limit to remain fixed by default.
- Optional future mode: raise limit in strict stages when trend accelerates.
- Log every recommendation/update and user override.

## Constraints
- Must handle barriers where KO liquidation differs from normal stop behavior.
- Must account for API order-update support and fall back to manual recommendation if unsupported.
- Must not over-tighten every tick; use candle closes, cooldown, and minimum step.

## Acceptance criteria
- Given a simulated trade path, stop updates match expected state transitions.
- Stop cannot be widened through the trade manager.
- User can see why a stop update is recommended.

## Testing notes
- Unit-test long and short state machines.
- Replay the example workflow: +1R → stop to break-even; further gain → trail/secure.
