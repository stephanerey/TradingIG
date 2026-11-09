# TradingIG domain risk register

| Risk | Required control |
|---|---|
| Wrong account context | Require explicit broker confirmation; isolate every intent by `AccountRef`. |
| Concurrent double opening | Evaluate and reserve global/underlying capacity under one lock. |
| Unknown FX or exposure | Mark state incomplete and veto new openings. |
| Daily loss breach | Block only new exposure; retain risk-reducing capability. |
| Distinct products hide common exposure | Aggregate by canonical economic underlying, not EPIC. |
| AI or UI bypasses a veto | Keep risk evaluation deterministic and outside presentation/AI layers. |
| Accidental live execution | Preserve `LiveTradingDisabledError`; R03 exposes no broker command path. |
| Partial/corrupt migration | Transaction, pre-migration backup, integrity check and restoration on failure. |
| Journal history rewritten | SQLite update/delete triggers plus append-only repository API. |
| P&L rounding or double counting | Decimal text values, unique event IDs and realized-only deterministic aggregation. |
| Secret leakage into journal/settings | Recursive forbidden-key checks and existing config secret exclusion. |
| Capability inferred without exact DEMO evidence | Default every execution capability to `UNSUPPORTED`; bind sanitized evidence to the exact DEMO account type and product family. |
| Read-only DEMO authorization mistaken for mutation authority | Keep broker mutation methods hard-blocked and require a separate explicit human authorization before any create/update/cancel/close probe. |
| Look-ahead bias | Indicators consume only closed candles and preserve observation timestamps. |
| Missing context boosts a candidate | Keep the component unavailable and downgrade to explicit `NO_TRADE` when required. |
| Malformed or hallucinated AI context is accepted | Validate an exact typed schema and require every cited signal to be active, fresh and present in the deterministic macro state. |
| AI provider failure fabricates a benign regime | Degrade to explicit `UNAVAILABLE/UNKNOWN` with no confidence or cited source; never infer a favorable fallback. |
| LLM output becomes an indicator or order instruction | Keep deterministic indicators and all execution/risk boundaries outside the provider schema. |
| An aligned AI/Scanner result is mistaken for execution approval | Emit only an expiring advisory directive without account or quantity; require a separate ticket, deterministic Risk Engine decision, AUTO policy gate and broker capability before any future execution intent. |
| External AI leaks account/trading secrets or incurs unapproved cost | Send normalized context only, inject a redacted secret, pin endpoint/model explicitly, disable storage and require human approval before the first live call. |
| News/source text injects instructions into AI analysis | Mark every supplied label, summary, URL and tag as untrusted data in the higher-priority prompt; expose no tools and validate the exact output schema and cited signal IDs. |
| Gray news evidence is mistaken for a deterministic favorable signal | Reserve the `ai_evidence` tag for citation only; retain gray severity, null score/confidence and exclude these records from ribbon details and macro aggregates. |
| A validated OpenAI probe silently enables recurring paid calls | Keep model authorization in memory for the session and require a separate, non-persisted acknowledgement before enabling the 15-minute context timer; otherwise every real analysis remains manual. |
| Unlicensed news content is retained | Require explicit usage-rights metadata; allow only bounded summaries when summary use is declared, otherwise retain metadata only. |
| Context flag cannot be traced to source evidence | Require existing normalized source record IDs, observation ordering and duplicate/future checks before producing a `ContextSignal`. |
| Unknown source rights produce favorable context | Convert the affected signal to gray with no score or confidence. |
| External feed redirects or injects untrusted links | Require HTTPS and an exact configured hostname allowlist for feed responses and item links. |
| Large or malformed XML exhausts the application | Bound timeout, payload and item counts; reject DTDs, invalid XML and unsupported content types. |
| Headline text is mistaken for calibrated market impact | Retain official metadata with `UNKNOWN` importance until a separately validated assessment supplies evidence. |
| News collection failure blocks or improves analysis | Return an explicit unavailable provider snapshot with no items; never infer a benign state. |
| Score mistaken for probability | Store/render ranking semantics and deterministic component commentary. |
| Contradictory strategies hidden | Preserve individual signals and emit explicit divergence reason codes. |
| Paper flow leaks to IG | Keep PaperBroker structurally independent and assert protected IG methods remain hard-blocked. |
| Duplicate simulated fill | Make submission idempotent by immutable intent ID and lock transition/fill creation. |
| Pending triggers on stale or incomplete data | Revalidate freshness, expiry, market/product, macro and risk at trigger time. |
| Wick falsely satisfies close rule | Use only a closed candle close for close-confirmed trigger types. |
| Stop protection is weakened | Reject automatic widening and advance state only after confirmed tighter protection. |
| AUTO inferred from a successful DEMO probe | Require a separate activation record, exact policy digest, runtime generation and explicit whitelists. |
| Restart silently restores AUTO | Start in ANALYSIS with kill switch active and reconciliation incomplete; invalidate prior runtime binding. |
| Ambiguous broker state coexists with a new AUTO entry | Veto readiness while any ambiguous execution remains unresolved. |
| Current read-only capability is treated as executable | Require explicit place-order and DEMO-execution capabilities; current IG adapter remains unsupported. |
| Replay consumes future information | Require explicit UTC latest-source and decision timestamps and reject `source > decision`, post-fill decisions or non-chronological sequences. |
| Incomparable experiments are ranked together | Bind results to dataset/rules/strategy/code/currency/fill/precision provenance and reject mixed comparisons. |
| Synthetic fixture profit is mistaken for strategy evidence | Label fixtures as mechanics-only and require a versioned real dataset plus out-of-sample/walk-forward evidence before any AUTO acceptance. |
| Full candle OHLC is exposed at its opening timestamp | Advance the replay clock to timestamp plus declared resolution and expose only prefixes closed by an explicit UTC boundary. |
| Current chart candle is silently treated as historical | Require a caller-supplied availability boundary and exclude intervals whose theoretical close is later. |
| Replayed strategy emits a signal for another experiment or instrument | Require exact strategy ID, rules version and instrument agreement before retaining signal evidence. |
| Strategy bypasses replay warmup or rewrites decision order | Reject `READY` before declared warmup, early/backward decisions and duplicate signal IDs; propagate errors without fallback. |
| Replay signal becomes an implicit order | Keep orchestration signal-only with no ticket, risk reservation, Paper fill or IG dependency. |
| Dataset ID/version points to changed content | Bind validation plans to a canonical SHA-256 over metadata and all OHLCV observations; reject mismatches. |
| Hidden split defaults or overlapping partitions bias validation | Require explicit positive train/validation/test/step sizes and contiguous chronological partitions with unused tail reported. |
