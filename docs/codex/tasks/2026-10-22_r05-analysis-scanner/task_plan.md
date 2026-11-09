# R05 analysis and scanner

## Objective

Implement deterministic technical indicators, structured macro context and an explainable advisory scanner without any execution path.

## Smallest sufficient approach

- Pure service/domain code independent from Qt and brokers.
- Numeric reference fixtures for a bounded initial indicator set.
- Explicit `READY`, `WARMING_UP` and `INVALID` data states.
- Explicit `NO_TRADE`, veto reasons, component provenance and deterministic commentary.
- Normalized 0–100 ranking score labelled as a ranking, never a probability.
- Missing sentiment/context remains missing or vetoes according to policy; it never improves a score.

## Exclusions

- No broker action, LLM, external provider, copyrighted news content, new dependency or black-box model.
- No automatic ticket generation and no R06 paper execution.

## Method skills

- `aurora-architecture-check` for strategy/scanner contracts and consumers.
- `aurora-domain-skill-factory` because no validated local skill covers analysis/scoring semantics.

## Gate

Human validation of the proposed `codex-tradingig-analysis-scanner` skill before business-code mutation.

## Planned proof

Numeric fixtures, warmup/invalid/no-trade cases, missing-context behavior, provenance/commentary, ranking determinism, full pytest, Ruff and SR post-check.
