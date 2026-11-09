# R00/R01 task plan

## Objective

Establish a reproducible offline baseline, then reproduce and minimally correct only: cache access at exhausted REST quota, M1-to-M5 OHLC/revision aggregation, and non-blocking slow historical loads in Qt. Stop after R01.

## Authority and scope

User approval covers the bounded SR00 → R00 → R01 pass. Allowed: project `.venv`, declared development dependencies, focused source/tests, factual task evidence, and offline Windows GUI checks. Forbidden: authenticated IG calls, live orders, trading activation, protection weakening, new application dependencies, schema migrations, R02+, or the R03/R04 settings-inheritance decision.

## Skills

- `aurora-lot-runner`: execute the validated two-lot R00/R01 pass without micro-gates.
- `aurora-diagnose`: reproduce each reported defect, establish cause, apply the smallest correction, and verify it.

## Plan

1. R00: install only declared project/dev dependencies into `.venv`; record Python/package state, full pytest, Ruff, format, import and safe offline GUI smoke results.
2. Inspect the focused market-data/cache/aggregation/Qt paths and associated tests.
3. For each R01 defect, reproduce with deterministic local/fake evidence; if present, add durable regression coverage and a minimal patch.
4. Run focused checks, then the proportionate full verification and diff review.
5. Update factual task/current-state evidence only as needed and stop before R02.

## Planned proof

- Baseline command results and concrete limitations.
- Cache regression at exhausted quota.
- Five-M1 aggregation/revision regression.
- Slow fake history provider Qt responsiveness regression.
- Focused pytest/Ruff plus full suite when feasible; no network credentials.

