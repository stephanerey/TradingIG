# Decisions

- Always subscribe the stable five-reference baseline in its approved order.
- Put the selected exact chart source first and deduplicate it against the baseline; the bounded
  universe therefore contains five or six items.
- Preserve one canonical in-memory series per reference EPIC and project it through exact product
  bindings later.
- Ignore an unexpected chart item explicitly in diagnostics; never infer a product/underlying link.
- Skip account switching when the persisted selection already equals IG's authenticated current
  account; retain the exact confirmation check for a genuinely different selected account.
- On a grouped-chart permission refusal, retry exactly once with the selected chart source only.
  Do not loop, probe other markets or broaden permissions; keep the Scanner explicitly degraded.
