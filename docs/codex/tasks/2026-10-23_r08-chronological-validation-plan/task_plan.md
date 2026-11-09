# Task plan — R08 chronological validation plan

## Objective

Add deterministic dataset fingerprinting plus explicit train/validation/test and rolling
walk-forward plans without selecting a strategy or computing performance.

## Authority and limits

- Authorized by the user's request to continue R08 offline development.
- No implicit ratios or optimization choices; every window size and step is caller-supplied.
- No strategy, score, ticket, fill, broker call, AUTO activation, persistence, migration,
  dependency or GUI wiring.
- Plans contain metadata and indices only; they do not expose or copy partition data.

## Selected project skills

- `codex-tradingig-analysis-scanner`
- `codex-tradingig-paper-execution`

## Approach

1. Define immutable fingerprint, partition, fold and validation-plan contracts.
2. Hash canonical dataset metadata and candle values with SHA-256.
3. Build one exact contiguous train/validation/test split from explicit point counts.
4. Build rolling walk-forward folds from explicit window and step sizes.
5. Report unused tail points and reject dataset/plan fingerprint mismatch.

## Verification

- Stable fingerprints and change detection.
- Exact split chronology and non-overlap.
- Deterministic rolling windows and explicit unused tail.
- Invalid sizes, insufficient history and dataset mismatch rejection.
- Protected replay/analysis/Paper/IG regressions and full offline suite.

## Stop condition

Stop after generic validation planning. Do not select a strategy or dataset, consume partitions,
optimize parameters, calculate performance or claim out-of-sample acceptance.
