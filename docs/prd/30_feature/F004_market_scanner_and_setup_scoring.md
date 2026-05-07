# F004 — Market Scanner and Setup Scoring

> **PRD Policy:** **PROJECT (editable)** — Feature specification.  
**Last updated:** 2026-05-07


## Goal
Rank configured instruments and indicate whether a trade is attractive, possible, or should be skipped.

## Non-goals
- No black-box ML in MVP.
- No guarantee of profitability.

## Requirements
- Consume `MacroRibbonState` from the macro context engine so scanner rows can display red/yellow/green macro flags next to technical setup scores.
- Monitor configured instruments: US Tech 100, France 40, Germany 40, Spot Gold.
- Compute technical context: trend, recent impulse, pullback, support/resistance proximity, volatility, relative strength, distance from recent highs/lows.
- Produce a setup score and explanation.
- Explicitly support `NO_TRADE` output.
- Avoid recommending entries that are too extended, too close to KO, or with poor R/R.
- Consider correlation/exposure: avoid stacking multiple similar risk-on/risk-off trades.

## Constraints
- Scores must be explainable and logged.
- Scanner output is advisory and must pass the risk engine before ticket creation.

## Acceptance criteria
- Scanner produces a ranked list with reason codes.
- At least one scenario returns `NO_TRADE`.
- Recommendations can be replayed from historical candle data.

## Testing notes
- Unit-test scoring components.
- Replay screenshots-derived scenarios when data is available.
