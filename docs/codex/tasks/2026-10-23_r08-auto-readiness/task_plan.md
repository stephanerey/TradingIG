# Task plan — R08 AUTO readiness

## Objective

Add a broker-independent, default-deny AUTO readiness contract. It must not activate AUTO, call IG,
persist an activation, or weaken any execution protection.

## Authority and scope

- User instruction: continue after R07 completion.
- Authorized: offline domain/service code, synthetic tests and phase documentation.
- Not authorized: AUTO activation, broker mutation, authenticated IG call, LIVE access, dependency,
  migration, scheduled task or GUI redesign.

## Selected project skills

- `codex-tradingig-accounts-risk`
- `codex-tradingig-supervised-demo-gate`

The Paper execution rules were consulted for boundary compatibility, but the Paper broker is not a
target of this lot.

## Smallest sufficient approach

1. Define immutable AUTO policy, activation/readiness inputs and deterministic rejection reasons.
2. Implement a pure gate with no broker import or submission method.
3. Require exact account/product/strategy whitelists, independent risk approval, proven capability,
   inactive kill switch, completed reconciliation, matching runtime generation and quota headroom.
4. Keep LIVE structurally forbidden under the current project authority.
5. Prove safe restart by showing that a new runtime generation invalidates an old activation.

## Verification

- Targeted unit tests for every veto and the all-green synthetic DEMO case.
- Protected IG adapter/order regressions.
- Full offline pytest suite, Ruff and diff check.

## Stop condition

Stop after the offline readiness gate. Do not connect it to GUI, IG adapters or an execution
coordinator, and do not start an R08 activation pass without a separate human decision.
