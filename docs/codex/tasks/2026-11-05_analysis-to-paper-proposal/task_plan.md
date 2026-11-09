# Analysis directive to Paper proposal

## Objective

Convert an unexpired `READY` analysis directive into an explicit Paper-only ticket draft and Risk
Engine request without submitting, filling or reserving anything.

## Scope

- Preserve the dirty worktree; no branch, commit, dependency, deletion, network or secret access.
- Skills: `codex-tradingig-analysis-scanner`, `codex-tradingig-accounts-risk`,
  `codex-tradingig-paper-execution`, `aurora-architecture-check`.
- Require explicit Paper account, quote, quantity, KO assumption and fill assumptions.
- No `PaperBroker.submit`, pending trigger, IG adapter or AUTO activation.

## Smallest sufficient approach

1. Add a paper-proposal envelope retaining directive/scanner provenance.
2. Validate directive status, expiry, product identity, signal identity and entry zone.
3. Delegate level/cost construction to the existing `TicketBuilder`.
4. Return the matching `RiskRequest`; leave the independent Risk Engine as the next gate.

## Verification

- Valid BUY/SELL handoff and explicit rejection fixtures.
- Protected execution regressions, full suite, Ruff, format and diff checks.

