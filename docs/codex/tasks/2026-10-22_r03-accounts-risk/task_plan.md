# R03 accounts and risk

## Objective

Implement the R03 account and conservative risk invariants without enabling broker execution.

## Scope

- Explicit account state and isolation.
- Validated inheritance: `global -> account -> strategy -> market`.
- Default 1% per-trade and 3% daily-loss gates.
- Global and underlying exposure limits, including concurrent reservations.
- Conservative veto for missing critical FX or exposure data.

## Exclusions

- No real or demo order submission.
- No weakening of `LiveTradingDisabledError`.
- No persistence migration, dependency, or R04 work.

## Method skills

- `aurora-architecture-check`: contract boundaries and consumer closure.
- `aurora-domain-skill-factory`: required because no project domain skill is declared.

## Gate

Generate and validate the proposed local `codex-tradingig-accounts-risk` skill before business-code mutation.

## Planned proof

Targeted account/risk tests, full pytest, Ruff, protected-order regression and SR post-check.
