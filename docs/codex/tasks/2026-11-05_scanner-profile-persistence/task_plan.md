# Scanner profile persistence

## Objective

Persist scanner strategy profile patches without secrets and resolve them with the approved
`global -> IG account ID -> StrategyId -> canonical underlying` precedence.

## Scope and assumptions

- The existing dirty worktree is preserved; no branch, commit, dependency or deletion.
- Account keys are IG account IDs, strategy keys are `StrategyId` values, and market keys are
  explicit canonical underlying IDs supplied by callers.
- This task adds no broker command, ticket, order or automatic execution path.
- The `codex-tradingig-analysis-scanner` skill and its R05 rules apply.

## Smallest sufficient approach

1. Add immutable typed persistence contracts for patches and their lookup catalog.
2. Store the catalog in `AppConfig`, preserving it through the Settings dialog.
3. Add exact-key catalog resolution to the existing profile resolver.
4. Cover typed round trips, precedence, malformed input and settings preservation.

## Verification

- Targeted profile/config/settings tests.
- Full test suite and protected order/DEMO regressions.
- Ruff and diff integrity checks.

