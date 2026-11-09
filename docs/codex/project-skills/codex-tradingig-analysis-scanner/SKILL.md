---
name: codex-tradingig-analysis-scanner
description: >-
  Apply TradingIG deterministic analysis and scanner rules when changing indicators, strategy signals, macro context, scoring, ranking or commentary. Use it to enforce closed-data provenance, explicit warmup/invalid/no-trade states, non-probabilistic scores and conservative treatment of missing context without creating an execution path.
---

# TradingIG analysis and scanner

Read `references/rules.md` before changing indicators, strategies, macro context or scanner behavior.

## Non-negotiable boundary

- Use only closed candles unless a contract explicitly labels a real-time update.
- Return `WARMING_UP` or `INVALID` instead of manufacturing an indicator value.
- Treat scanner scores as bounded ranking values, never probabilities or promises.
- Keep missing sentiment/context unavailable; never replace it silently with a favorable score.
- Preserve component values, weights, provenance, reason codes and deterministic commentary.
- `NO_TRADE` and safety vetoes always override the numeric ranking.
- Never submit or prepare a broker command from scanner code.

## Required closure

- Verify numeric fixtures and insufficient/invalid data.
- Verify missing context, vetoes, score normalization and deterministic ordering.
- Verify macro freshness/source provenance and explicit gray/unknown degradation.
- Run full tests and protected-order regressions.
