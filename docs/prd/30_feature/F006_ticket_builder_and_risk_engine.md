# F006 — Ticket Builder and Risk Engine

> **PRD Policy:** **PROJECT (editable)** — Feature specification.  
**Last updated:** 2026-05-07


## Goal
Generate a complete IG ticket proposal and validate it against strict risk rules.

## Non-goals
- The ticket builder does not decide the trade alone; it consumes setup/product/risk inputs.

## Requirements
- Include the current `MacroRibbonState` snapshot in ticket validation and warnings. Red/high event-risk status should require explicit confirmation or apply configured risk reduction.
- Inputs: account capital, selected product, direction, entry/current price, KO/barrier level, stop distance/level, limit distance/level, desired risk, min/max size, fees/prime/cost where available.
- Outputs: quantity, stop, limit, expected loss, expected gain, R/R ratio, R value, KO distance, warnings, rejection reasons.
- Enforce max risk per trade.
- Enforce max exposure across open positions.
- Reject tickets with invalid KO distance, poor R/R, stale data, unsupported product, or excessive size.
- Support long and short calculations.

## Constraints
- All calculations must be deterministic and unit-tested.
- No UI widget may bypass risk validation.

## Acceptance criteria
- Given known examples, engine computes the same expected stop loss and target gain as manual calculation.
- Oversized quantities are rejected.
- User override is possible only with explicit warning and journal event, not silently.

## Testing notes
- Unit-test numerical calculations with tolerance.
- Test edge cases: min size, currency conversion, zero/negative stop distance, stale quotes.
