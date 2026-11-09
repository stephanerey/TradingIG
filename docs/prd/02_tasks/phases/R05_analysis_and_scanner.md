# R05 — analysis and scanner

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstruction.

**Last updated:** 2026-11-04

**Status:** COMPLETED locally on 2026-10-22. Evidence: 153 offline tests, targeted Ruff/format checks and SR post-check; no broker execution path.

**Prerequisite:** [R04](R04_storage_and_workspace.md) completed with actual evidence. [Canonical source sequence and SR boundaries](../../05_coding_agent/sr41_development_workflow.md).

## Goal

Implement reproducible indicators, strategies, context and explainable scanner.

## Non-goals

No task is launched by reading this specification. No automatic branch switch, dependency installation, broker action or deployment.

## Constraints

Score is not a probability; missing sentiment cannot silently improve the result.

## Acceptance criteria

Numeric fixtures, WARMING_UP/INVALID, NO_TRADE, provenance and score commentary are verified.

## Testing notes

Use phase-appropriate unit/contract/replay or native Windows UI checks from [the acceptance matrix](../../90_quality/acceptance_matrix.md) and [testing strategy](../../90_quality/testing.md). Record actual commands, results and limitations; do not mark acceptance based only on this document.

## Requirement references

- [Source chapter 7](../../30_feature/F004_market_scanner_and_setup_scoring.md)
- [Source chapter 11](../../30_feature/F005_macro_news_context_engine.md)

## Completion evidence and boundary

- SMA, EMA, RSI and ATR use closed, ordered UTC candles and expose `READY`, `WARMING_UP` or `INVALID` with provenance.
- The strategy registry is broker-independent; individual signals are preserved and BUY/SELL divergence is explicit.
- The normalized ranking retains all six components and weights; missing components or vetoes force `NO_TRADE`, and commentary states that the score is not a probability.
- Structured context becomes gray/unknown when absent or stale; the Qt ribbon renders value plus textual severity, source and timestamp.
- External providers, LLM output and concrete strategy formulas not defined by the PRD remain unconfigured rather than guessed.
- R05-AI1 adds the provider-neutral typed `MarketContextSnapshot` boundary required by F005:
  exact structured output, source/model/prompt/time/confidence provenance and explicit
  `UNAVAILABLE/UNKNOWN` fallback are covered offline. No real provider or LLM is connected yet.
- R05-CTX1 adds provider-neutral macro/news records, adapter protocols and deterministic lineage/
  rights checks before producing `ContextSignal`; no real source or payload mapping is connected.
- R05-SRC1 adds bounded read-only Federal Reserve and ECB RSS adapters with explicit collection
  health. Live source availability is proven, but no scheduler, Qt refresh or headline assessment
  is connected.
- R05-SRC2 refreshes those providers outside the Qt event loop at startup, every 15 minutes and on
  explicit request. Only source health reaches the ribbon; scores and market aggregates remain
  unknown. No headline assessment, AI provider or broker path is connected.
- R05-AI2 implements a disabled-by-default OpenAI Responses adapter with an explicit model, an
  injected redacted key, strict structured output, bounded HTTPS and conservative error/refusal
  degradation. A Settings > OpenAI gate exposes a single synthetic test through a `QThread`, while
  keeping the key masked and requiring explicit model/cost/data acknowledgement. Runtime scanner
  composition still requires successful human validation.
- R05-AI3 composes the validated provider into a session-only, manual consultative runtime. Up to
  20 permitted official headlines are represented as gray `ai_evidence` without deterministic
  score or confidence. A dedicated Qt worker runs only after a successful Settings probe and an
  explicit manual/cost action; its typed result is rendered separately and cannot reach tickets,
  risk or broker code. The first real news-context result was validated by the user on 2026-11-05.
- R05-AI4 optionally refreshes that same consultative context every 15 minutes after a distinct,
  non-persisted session consent and successful probe. Missing evidence, missing key or an active
  call skips the cycle; no account, ticket or order data enters the request.
- R05-CTX2 deterministically projects normalized `HIGH` macro events into red event-risk flags
  inside caller-supplied pre/post windows. Other importance levels remain uninterpreted, unknown
  usage rights degrade to gray, and no external calendar provider or broker path is introduced.
- Scanner profiles can now resolve atomic leaf patches in `global -> account -> strategy -> market`
  order with per-value provenance. A separate advisory directive core can require exact Scanner,
  consensus and AI alignment under an explicit policy, but emits no account, quantity, ticket,
  `OrderIntent` or broker command.
- Profile patches now have a strict secret-free typed JSON representation in `AppConfig`. Exact
  lookup keys are IG account ID, `StrategyId` and caller-supplied canonical underlying; Settings
  preserves this catalog even though no profile editor is exposed yet. Product-to-underlying
  inference remains forbidden until an explicit mapping contract is chosen.
- The initial canonical-underlying type is limited to `US_TECH_100`, `FRANCE_40`, `GERMANY_40`,
  `SPOT_GOLD`, and `US_CRUDE`. The existing explicit instrument registry must supply one of those
  exact values; aliases and unknown mappings fail closed.
- A market batch can now evaluate independently resolved single-strategy profiles for all three
  technical strategies, preserve their exact leaf provenance and rebuild consensus only after all
  signals are present. The legacy single-profile input remains supported; the provisional Qt tab
  is not yet wired to this batch core.
