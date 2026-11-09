# R06 paper broker and trade manager

## Objective

Implement and verify a deterministic paper-only execution flow: immutable ticket/intents, PaperBroker, software pending-order state machine, stop protection/trailing and local alerts, with proof that no IG order method is called.

## Smallest sufficient approach

- Reuse `OrderIntent`, `AccountRef`, `RiskEngine`, journal contracts and normalized macro state.
- Add a distinct in-memory `PaperBroker` implementing the broker contract without importing or delegating to `IGRestAdapter`.
- Keep fill, spread, fees, slippage, KO and gap behavior explicit and fixture-driven.
- Make pending transitions monotonic, expiry/staleness-aware and exactly-once under locking.
- Make stop proposals direction-aware, cooldown/minimum-step aware and impossible to widen automatically.
- Keep alerts local/in-memory in R06; no external notification provider or secret.

## Exclusions

- No LIVE or DEMO IG order, adapter activation, authenticated broker call, SMTP/Telegram or dependency.
- No modification or weakening of `LiveTradingDisabledError`.
- No R07 capability qualification and no AUTO mode.

## Method skills

- `aurora-architecture-check` for the execution boundary and consumers.
- `aurora-domain-skill-factory` because no validated local skill covers paper fills, pending transitions or stop invariants.

## Mandatory gate

Obtain human validation of the proposed `codex-tradingig-paper-execution` skill boundary before generating the skill or mutating business code.

## Planned proof

Deterministic long/short fills, costs/slippage/KO, idempotent intent handling, exactly-once pending trigger, wick/close/expiry/staleness cases, macro/risk revalidation, non-widening stops, confirmation-dependent protection, journal transitions, full tests and protected IG-order regressions.
