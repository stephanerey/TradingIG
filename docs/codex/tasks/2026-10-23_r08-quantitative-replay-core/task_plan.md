# Task plan — R08 quantitative replay core

## Objective

Add a deterministic, offline summary for closed Paper positions with explicit experiment
provenance, net P&L, R metrics, drawdown and temporal no-look-ahead validation.

## Authority and limits

- Authorized by the user's request to continue R08 offline development.
- No AUTO activation, broker call, strategy recommendation, external data, dependency, migration,
  persistence or GUI wiring.
- Synthetic fixtures validate mechanics only and are not profitability evidence.

## Selected project skills

- `codex-tradingig-paper-execution`
- `codex-tradingig-accounts-risk`

## Approach

1. Define immutable experiment, closed-trade evidence and metrics contracts.
2. Require UTC chronology: latest source <= decision <= fill/open < close.
3. Require closed Paper positions, declared fill model, single currency and positive initial risk.
4. Compute deterministic net P&L, total/expectancy R, win rate and peak drawdown.
5. Compare management modes only for the same dataset/rules/strategy/currency provenance.

## Verification

- Normal metrics and comparison.
- Look-ahead, reverse chronology, mixed provenance/currency and open-position rejection.
- Protected Paper/IG regressions and full offline suite.

## Stop condition

Stop after the generic replay core. Do not select or optimize a trading strategy and do not claim
quantitative AUTO acceptance from synthetic fixtures.
