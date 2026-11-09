# Verified Barrier bindings

## Objective

Extend the exact Scanner product bindings with the unambiguous France 40, Germany 40 and US Crude
Barrier Buy/Sell products observed in the local LIVE discovery evidence.

## Boundaries

- Exact EPICs and canonical reference EPICs only.
- No name-based runtime inference and no authenticated IG request.
- Keep Spot Gold unbound while two indistinguishable Barrier pairs remain in the evidence.
- No ticket, broker, order, AUTO or GUI redesign.

## Skill

- `codex-tradingig-analysis-scanner`

## Follow-up: option changes and reference streaming

- Diagnose the displayed option variations from existing discovery data.
- Display option variations as unqualified until their meaning is verified; retain original data.
- Check IG's official streaming reference and disable the obsolete automatic MARKET probe.
- Verify the product table, streaming behavior, protected execution boundaries and full suite.

## Follow-up: quote-candle correctness

- Skill: `codex-tradingig-analysis-scanner`.
- Correct MID extrema from observed quotes, reject out-of-order updates and parse IG PRICE timestamps.
- Keep fallback product-only, without Scanner projection, history, orders or new external access.
- Verify numeric counterexamples, focused UI/data tests and the full/protected suites.
- Isolate quote aggregation across account and environment switches.

## Follow-up: DEMO France CFD Scanner

- Add only the exact human-observed France 40 CFD self-binding; do not infer other products.
- Verify the default, session ingestion and full Scanner batch with synthetic DEMO candles.

## Follow-up: option variation consistency

- Keep unverified option variation unavailable in the chart header as well as the product table.
- Preserve variations for a distinct selected chart source such as an underlying CFD.

## Follow-up: streaming error scope

- Restrict the group chart fallback to permission errors for the current grouped CHART scope.
- Verify PRICE errors and mismatched chart group errors do not restart or clear Scanner streams.

## Follow-up: quote isolation across connections

- Skills: `codex-tradingig-analysis-scanner`, `codex-tradingig-paper-execution`.
- Invalidate stored quotes, chart/Scanner displays and pending Paper evaluations on disconnect,
  new connection and account changes; isolate late events using stream generations.
- If an account switch fails, invalidate data and disconnect instead of displaying or saving an
  unconfirmed account. Verify this behavior and protected regressions.

## Follow-up: logging and quote display provenance

- Skill: `codex-tradingig-accounts-risk`.
- Mask the account identifier in future quote-subscription logs while preserving wire item names.
- Keep session quotes visible after table filtering without resetting their Paper freshness time;
  distinguish session values from discovery snapshots with tooltips.

## Follow-up: explicitly delayed quotes

- Skills: `codex-tradingig-accounts-risk`, `codex-tradingig-paper-execution`.
- Preserve IG's DELAY marker and prevent explicitly delayed quotes from authorizing Paper tickets,
  triggering/closing Paper positions or supplying the Scanner spread. Missing flags remain unknown
  and retain existing behavior; this does not claim quote freshness is otherwise verified.

## Follow-up: bounded freshness and connection invalidation

- Skills: `codex-tradingig-accounts-risk`, `codex-tradingig-paper-execution`.
- Reuse the ticket's 30-second receipt window for Scanner spread and Paper mark/manual close.
- Invalidate Paper market quotes on disconnect/account change and refresh its view on opening.
- Verify exact freshness boundaries, restore, disconnect and no unintended Paper fills.

