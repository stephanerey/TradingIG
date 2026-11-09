# Verification

- Navigation/discovery/adapter/profile targeted regressions after DEMO schema correction:
  `51 passed`.
- Chart resolver/config/context targeted regressions after exact-mapping enforcement:
  `86 passed`.
- Protected IG connection/streaming/REST/DEMO/risk/ticket/Paper regressions: `62 passed`.
- Full offline suite after exact chart-mapping enforcement: `526 passed in 23.18s`.
- `ruff check src tests`: passed.
- Targeted format check: 7 files already formatted.
- SR Method 4.1 pack verification: coherent.
- `git diff --check`: no whitespace error; only pre-existing LF→CRLF conversion warnings.
- Bounded authenticated DEMO read-only evidence: login, categories, `INDICES` and `COMMODITIES`
  metadata, search/schema checks and logout. No account identifier or secret was recorded; no
  switch, ticket, order, position mutation, dependency, branch, commit, AUTO or LIVE activation.
