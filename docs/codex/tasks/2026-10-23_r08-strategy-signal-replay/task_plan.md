# Task plan — R08 strategy signal replay

## Objective

Evaluate one injected strategy deterministically over the future-blind replay frames and retain
auditable source-to-signal evidence.

## Authority and limits

- Authorized by the user's request to continue R08 offline development.
- No concrete strategy selection or implementation, optimization, scoring formula, ticket, pending
  order, Paper fill, broker call, AUTO activation, persistence, migration, dependency or GUI.
- Synthetic strategies validate orchestration only and are not performance evidence.

## Selected project skills

- `codex-tradingig-analysis-scanner`
- `codex-tradingig-paper-execution`

## Approach

1. Define immutable signal evidence joining a replay frame and `StrategySignal`.
2. Validate strategy/rules/instrument identity and source-before-decision chronology.
3. Invoke the existing `Strategy` protocol once for every cumulative frame.
4. Preserve warmup frames and combine dataset/input/signal provenance.
5. Reject backward decisions and propagate strategy errors without fallback.

## Verification

- Deterministic call order and visible-prefix sizes.
- Warmup frame preservation and combined provenance.
- Strategy, version, instrument, early/backward time rejection.
- Strategy exception propagation.
- Protected analysis/Paper/IG regressions and full offline suite.

## Stop condition

Stop after generic signal orchestration. Do not choose or implement a strategy, score signals,
construct intents, simulate fills or claim quantitative acceptance.
