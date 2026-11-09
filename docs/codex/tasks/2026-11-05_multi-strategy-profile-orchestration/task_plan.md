# Multi-strategy profile orchestration

## Objective

Let one multi-market Scanner batch evaluate independently resolved technical profiles for
`TREND_FOLLOW`, `BREAKOUT`, and `PULLBACK`, then rebuild one explicit consensus per market.

## Scope

- Preserve the dirty worktree; no branch, commit, dependency, deletion, network or secret access.
- Skills: `codex-tradingig-analysis-scanner`, `aurora-architecture-check`.
- Keep the existing single-profile input compatible.
- No Qt wiring, ticket, `OrderIntent`, broker command, Paper fill or AUTO activation.

## Smallest sufficient approach

1. Resolve a deterministic, non-empty set of single-strategy profiles through the approved
   catalog and explicit instrument mapping.
2. Accept those resolved profiles in `MarketScannerInput`, rejecting overlap and incoherence.
3. Evaluate closed candles per profile, merge signals, rebuild consensus and score once.
4. Retain resolved leaf provenance in each market batch item.

## Verification

- Per-strategy configuration, consensus, provenance, invalid selection and market isolation tests.
- Protected execution regressions, full suite, Ruff, format and diff checks.

