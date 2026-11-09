---
name: codex-tradingig-paper-execution
description: >-
  Apply TradingIG paper-execution safety rules when changing simulated tickets, fills, software pending orders, trade state transitions, stop protection or replay. Use it to keep paper execution deterministic, idempotent, risk-gated and structurally unable to call IG order methods.
---

# TradingIG paper execution

Read `references/rules.md` before changing paper fills, pending-order transitions, position lifecycle or stop management.

## Non-negotiable boundary

- Keep `PaperBroker` structurally separate from concrete IG adapters; it must neither import nor delegate to an IG order method.
- Accept only explicit paper account scope and an immutable intent that has passed the independent Risk Engine.
- Make intent submission idempotent: the same intent ID cannot create a second simulated fill or position.
- Treat ambiguous execution as `UNKNOWN` and require reconciliation; never retry blindly.
- Declare spread, fees, slippage, gap and KO assumptions in configuration or fixture provenance; never claim OHLC simulation is live-realistic.
- Revalidate expiry, data freshness, market/product status, macro state and risk at a software trigger.
- Lock pending transitions so one condition produces at most one trigger; wick-only data cannot satisfy a candle-close rule.
- Never widen a stop automatically. A protected/trailing state follows confirmation, not merely a proposal.
- Preserve every transition and reason through the append-only journal boundary.
- Do not weaken `LiveTradingDisabledError`, enable DEMO/LIVE execution, add external notifications or start R07 behavior.

## Required closure

- Verify deterministic long/short fills, costs, KO/gap cases and duplicate intents.
- Verify pending expiry, stale data, macro/risk vetoes, close confirmation and concurrent exactly-once behavior.
- Verify long/short non-widening stops, break-even after costs, cooldown/minimum step and confirmation-dependent states.
- Run the full offline suite and the protected IG-order regressions.
