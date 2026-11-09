# TradingIG business rules

## Accounts

- BR-ACC-001: every risk or execution intent carries an explicit account reference.
- BR-ACC-002: a failed or unconfirmed account switch does not change the effective account.
- BR-ACC-003: missing FX conversion makes consolidated state incomplete and vetoes a new opening when conversion is required.

## Risk

- BR-RISK-001: default per-trade risk is 1% of `min(E_ref_day, E_current)`.
- BR-RISK-002: daily net loss at 3% of `E_ref_day` blocks new openings, but not monitoring or risk-reducing actions.
- BR-RISK-003: default limits are one opening exposure globally and one per economic underlying.
- BR-RISK-004: open positions and in-flight reservations consume the same limits; reservation is atomic.
- BR-RISK-005: unknown critical exposure, unsupported product, stale critical price state, duplicate intent or unconfirmed account vetoes a new opening.
- BR-RISK-006: estimated stop loss includes anticipated costs and scenario slippage; barrier/KO maximum loss is checked separately when supplied.
- BR-RISK-007: financial vetoes cannot be overridden by market or AI scores.

## Settings precedence

The human-approved order is `global -> account -> strategy -> market`; a later, explicitly defined layer overrides an earlier one. Origins must remain inspectable.

Sources: REQ-ACC-001–007 and REQ-RISK-001–011 in the reconstructed V1.2 PRD.

## Storage and audit

- BR-REC-001: journal events are append-only, UTC-stamped and uniquely identified.
- BR-REC-002: corrections append a new correlated event; history is never silently overwritten.
- BR-REC-003: financial amounts use exact decimal representation and retain their currency/status.
- BR-REC-004: realized P&L totals include only explicitly realized events and never silently combine currencies.
- BR-REC-005: settings writes are atomic and exclude credentials, tokens and authentication material.
- BR-REC-006: an existing database is backed up before a version change and restored on migration failure.

## Analysis and scanner

- BR-SCAN-001: indicators consume closed candles and return explicit ready/warmup/invalid states.
- BR-SCAN-002: every signal and score component retains source/timeframe provenance and reason codes.
- BR-SCAN-003: unavailable context remains unavailable and cannot improve a ranking silently.
- BR-SCAN-004: scanner score is a normalized ranking, not a probability or profit promise.
- BR-SCAN-005: `NO_TRADE`, invalid critical data and safety vetoes override any numeric score.
- BR-SCAN-006: scanner output is advisory and cannot invoke a broker or bypass the Risk Engine.
- BR-AI-001: technical indicators remain deterministic inputs; an LLM cannot calculate or replace
  their authoritative values.
- BR-AI-002: an available AI analysis retains model, prompt, cited source signals, generation and
  validity timestamps, and declared confidence.
- BR-AI-003: missing, stale, untraceable or invalid AI output becomes explicitly unavailable and
  unknown; it cannot improve ranking or be treated as neutral-positive evidence.
- BR-AI-004: the typed AI context boundary cannot emit tickets, reservations, fills or broker
  commands, and cannot override financial or safety vetoes.
- BR-AI-005: an external AI request may contain only normalized market-context evidence and its
  provenance; model, secret source, prompt version, retention behavior and network activation must
  be explicit, and a first live/cost-incurring call requires human approval.
- BR-AI-006: raw authorized news metadata may be marked `ai_evidence` for model citation while
  remaining gray, score-free and confidence-free in deterministic macro aggregation.
- BR-AI-007: runtime OpenAI analysis is session-only. A successful explicit probe may enable either
  manual analysis or a separately acknowledged 15-minute refresh for that process; its displayed
  bias, risk and confidence remain consultative and cannot create or modify scanner, ticket or
  order state.
- BR-AI-008: combining an AI analysis with Scanner and strategy evidence may emit only a typed,
  expiring advisory directive. Unknown, stale, mis-scoped, directionally conflicting or policy-
  blocked evidence produces `NO_TRADE`; the directive contains no account, quantity or broker
  command and is not an execution authorization.
- BR-CTX-001: every normalized macro event and news item carries a stable source identity, UTC
  observation timestamp, category, importance and explicit usage-rights status.
- BR-CTX-002: a context flag must cite existing normalized source records and cannot predate their
  observation; future-dated or duplicate lineage is rejected.
- BR-CTX-003: evidence with unknown usage rights becomes gray/unavailable with no score or
  confidence; it cannot improve regime, bias or ranking.
- BR-CTX-004: provider-specific payload parsing and free-text interpretation remain outside the
  deterministic context core.
- BR-CTX-005: automated official feeds use HTTPS and an explicit hostname allowlist, bounded
  response size/time/item count, metadata-only retention and stable source-derived IDs.
- BR-CTX-006: a feed that omits calibrated market impact remains `UNKNOWN`; headlines cannot be
  converted silently into importance, severity, direction or score.
- BR-CTX-007: provider/network/payload failure produces an explicit unavailable collection and
  cannot remove deterministic context or create favorable evidence.

## Paper execution and trade management

- BR-PAPER-001: paper execution accepts only explicit paper account scope and never delegates to a concrete IG adapter.
- BR-PAPER-002: each immutable intent ID can create at most one simulated execution outcome.
- BR-PAPER-003: fills retain price, spread, fee, slippage, timing and model provenance; unknown precision is not presented as realism.
- BR-PEND-001: trigger-time expiry, freshness, market/product, macro and risk checks precede any transition to confirmation/execution.
- BR-PEND-002: a software pending condition triggers at most once under state locking; candle-close rules ignore wick-only crossings.
- BR-TRADE-001: automatic stop changes preserve or tighten protection and never widen it.
- BR-TRADE-002: a trade becomes protected or trailing only after execution-boundary confirmation.
- BR-TRADE-003: every intent, pending and trade transition is append-only auditable with explicit reason codes.

## Optional automation readiness

- BR-AUTO-001: AUTO starts disabled with the kill switch active and reconciliation incomplete.
- BR-AUTO-002: readiness requires an unexpired activation bound to the exact policy digest and
  current runtime generation; a restart invalidates the previous runtime binding.
- BR-AUTO-003: account, product and strategy must each belong to explicit whitelists; missing or
  empty provenance cannot be inferred from prior DEMO evidence.
- BR-AUTO-004: independent risk approval, proven broker capability, completed reconciliation,
  zero ambiguous executions and quota headroom are cumulative, non-overridable requirements.
- BR-AUTO-005: current project authority forbids LIVE AUTO regardless of other inputs.

## Quantitative replay

- BR-REPLAY-001: replay evidence is accepted only when `latest source <= decision <= simulated
  fill < close`, all timestamps are UTC, and every position is closed.
- BR-REPLAY-002: metrics use the recorded net realized Paper P&L and a strictly positive initial
  risk amount; currencies and fill-model versions cannot be mixed silently.
- BR-REPLAY-003: each experiment declares dataset, dataset version, strategy, rules, code revision,
  management mode, price precision and fill-model provenance.
- BR-REPLAY-004: management modes can be compared only under identical provenance, apart from the
  experiment identifier and management mode.
- BR-REPLAY-005: synthetic fixtures demonstrate deterministic mechanics only; they are never
  profitability evidence or AUTO acceptance evidence.
- BR-REPLAY-006: a chronological candle feed exposes every closed prefix in order and never a
  later candle; the full OHLC becomes available only at `candle timestamp + resolution`.
- BR-REPLAY-007: adapting an in-memory chart series requires an explicit UTC availability boundary
  and source provenance; candles not closed by that boundary are excluded.
- BR-REPLAY-008: strategy replay invokes an injected strategy once per visible prefix and binds
  every signal to the experiment strategy/rules, input instrument and source clock; duplicate IDs,
  backward/early decisions and premature `READY` states are rejected.
- BR-REPLAY-009: replay signal orchestration remains advisory and cannot construct tickets,
  reservations, fills or broker commands.
- BR-REPLAY-010: chronological validation plans bind to a canonical dataset SHA-256 and retain
  explicit train, validation, test and step sizes; no split ratio or optimization default is
  inferred.
- BR-REPLAY-011: train, validation and test partitions are non-empty, contiguous and ordered within
  each fold; rolling folds advance by their declared step and any unused tail remains explicit.
