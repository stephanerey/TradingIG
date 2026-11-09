# Paper proposal risk review

## Objective

Evaluate a current Paper proposal through the independent Risk Engine while granting no exposure
reservation or execution authority.

## Boundaries

- `RiskEngine.evaluate` only; never `evaluate_and_reserve`.
- No `PaperBroker.authorize` or `submit`, no IG adapter, no AUTO/LIVE path.
- Explicit UTC review time before intent expiry.
- Preserve the exact risk decision and resolved setting sources.

## Verification

- Approval and rejection fixtures, expiry and time-zone failures.
- Assert no reservation after either decision.
- Protected and full offline regressions, Ruff and format checks.
