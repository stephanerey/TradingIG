# F010 — Backtesting and Replay

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Earlier project text is preserved; explicit V1.2 changes take precedence only on documented conflicts. This is not implementation or activation evidence.


> **PRD Policy:** **PROJECT (editable)** — Feature specification.\
**Last updated:** 2026-10-22


## Goal
Replay historical market data and journaled sessions to test entry filters, software pending orders, and stop-management rules.

## Non-goals
- No over-optimized ML strategy in MVP.
- No guarantee that backtest results predict live performance.

## Requirements
- Load cached IG historical candles.
- Replay candles/ticks into scanner, pending-order engine, and trade manager.
- Compare modes: fixed target, break-even only, trailing by structure, trailing by ATR.
- Produce metrics in R and currency.
- Save replay configuration and results.

## Constraints
- Backtests must include spread/fees/slippage approximations where possible.
- Avoid look-ahead bias: only past data is available to rules.

## Acceptance criteria
- A known scenario produces deterministic replay results.
- Stop-management rules can be compared without live broker connection.

## Testing notes
- Use fixture datasets.
- Add tests for no look-ahead access.

## Implementation evidence — 2026-10-23

The first generic offline replay core is implemented. It summarizes closed `PaperPosition`
evidence deterministically into net P&L, total/expectancy R, win rate and maximum drawdown in
currency and R. Explicit UTC source/decision/fill/close chronology rejects look-ahead, and mode
comparison requires matching dataset, strategy, rules, code, currency, fill model and price
precision provenance.

This is partial evidence only: it does not yet load a versioned market dataset, replay candles into
the scanner/pending/trade-manager chain, persist experiments, implement train/test or walk-forward
validation, or validate an approved strategy. Synthetic tests prove mechanics, not profitability,
broker realism or AUTO readiness.

The second generic offline increment adapts an already loaded `ChartCandleSeries` into an immutable
versioned dataset and emits cumulative `IndicatorInput` frames. It validates UTC, closed/valid OHLC,
strict timestamp order and exact dataset ID/version binding. Every prefix remains visible so normal
indicator warmup applies; future intervals are excluded using an explicit UTC availability boundary,
and OHLC availability is timestamp plus candle resolution.

This increment performs no cache/file I/O itself and does not yet invoke a strategy, scanner,
pending-order engine, trade manager or PaperBroker.

The third generic offline increment invokes an injected implementation of the existing `Strategy`
protocol once per cumulative frame and records immutable frame-to-signal evidence. It enforces
experiment strategy/rules identity, input instrument identity, source-before-decision chronology,
monotonic decisions, unique signal IDs and declared warmup. Dataset, input and signal provenance
remain inspectable together.

This remains signal-only orchestration. No concrete strategy is selected or implemented, and no
scanner score, intent, risk reservation, pending order, fill or broker command is produced.

The fourth generic offline increment creates canonical SHA-256 dataset fingerprints and immutable
chronological validation plans. A caller must supply positive train/validation/test sizes and, for
rolling walk-forward, an explicit step. Each fold contains contiguous non-overlapping partitions;
folds advance by the declared step and any insufficient tail remains reported rather than reused.

This increment plans validation only. It does not expose partition data to a strategy, tune
parameters, aggregate fold results or prove out-of-sample performance.

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 14; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-14"></a>

## 14. Backtesting, paper trading et validation quantitative

**REQ-TEST-001/P1** PaperBroker simule ordres, positions, frais, spread, stop/TP, KO et slippage paramétrés avec les mêmes contrats que le broker réel.\
**REQ-TEST-002/P2** Replay chronologique OHLC/événements sans fuite temporelle, warmup identique à la production ; test et traçabilité du signal à l'exécution.\
**REQ-TEST-003/P2** Backtest avec prix bid/ask lorsque disponibles, horaires de marché, écarts, latence, frais, gaps et contraintes du produit. Précision insuffisante explicitement déclarée, pas de résultat « réaliste » sans données adaptées.\
**REQ-TEST-004/P2** Validation chronologique train/validation/test, walk-forward, comparaison au baseline et intervalles/incertitude lorsque applicables ; éviter optimisation sur le jeu final.\
**REQ-TEST-005/P2** ML et LLM doivent prouver valeur ajoutée hors échantillon en P&L ajusté du risque **et** stabilité (drawdown, performance par régime), avant activation en mode automatique.\
**REQ-TEST-006/P2** Versionner données, features, règles, code/commit et paramètres de chaque expérience.

## V1.2 traceability

[Chapter 4](../10_architecture/overview.md) · [Acceptance matrix](../90_quality/acceptance_matrix.md) · [Definition of Done](../90_quality/definition_of_done.md). Criteria are specifications, not passed test results.
