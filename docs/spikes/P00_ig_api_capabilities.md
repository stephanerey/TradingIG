# P00 IG API Capabilities Spike

**Status:** Draft template  
**Last updated:** 2026-05-07

## Scope

This spike documents the P00 read-only IG API foundation and the remaining unknowns that must be
validated before any live or semi-automated trading feature is designed.

## Implemented in P00

- Python package skeleton following `docs/prd/10_architecture/package_layout.md`.
- Safe configuration model with `demo/live`, username, selected account, `read_only`, and
  `enable_live_trading` flags.
- In-memory secret model for IG password and API key with redacted `repr` and string output.
- Credential store abstraction with test in-memory store and optional OS keyring adapter.
- IG REST adapter skeleton for:
  - login/logout;
  - `get_accounts()`;
  - `search_markets()`;
  - `get_market_details()`;
  - `get_prices()`.
- Hard blocking stubs for create/update/close position and working-order creation.
- Read-only CLI connectivity check: `trading-ig-assistant check-ig-connectivity`.

## Not implemented in P00

- GUI.
- Streaming/Lightstreamer connectivity.
- Product discovery service for Barriers or Options.
- Risk engine, ticket builder, trade manager, journal persistence.
- Any live order placement, position update, position close, or working-order execution.

## Unknowns to validate with IG demo API

### Barrier product discovery

- Which REST market-search terms and instrument filters expose Barrier contracts.
- Whether Barrier products are returned as distinct epics or under market details nodes.
- Which fields identify direction, expiry, barrier/KO level, spread, minimum size, and currency.

### Option product discovery

- Which REST market-search terms and instrument filters expose Option contracts.
- Whether options are discoverable through the same endpoint family as cash/DFB markets.
- Which fields identify strike, expiry, call/put direction, spread, minimum size, and currency.

### Available KO levels

- Whether available KO levels are exposed directly by market details, dealing rules, or separate
  product metadata.
- Whether KO levels change intraday and require refresh before ticket confirmation.
- Whether unavailable or stale KO levels produce a specific IG error code.

### Opening positions through API

- Whether Barrier and Option positions can be opened through the public REST API for the target
  account type and region.
- Whether the required ticket fields differ from standard OTC positions.
- Whether demo and live environments expose identical capabilities.

### Modifying stops and limits

- Whether stops and limits can be attached, modified, or removed for Barrier and Option products.
- Whether stop widening is rejected by IG or must be blocked only in local business rules.
- Which error codes indicate unsupported modifications versus invalid prices.

### Working orders

- Whether native working orders are available for Barrier and Option products.
- Whether working orders support the required direction/product/KO combinations.
- Whether unavailable native working orders require the MVP software pending-order workflow with
  manual confirmation.

## Required manual verification notes

Record each tested endpoint, environment, account type, epic, sanitized request shape, sanitized
response shape, and observed IG error code. Do not paste credentials, tokens, account IDs, or raw
auth headers into this document.

## P01 Product Discovery Findings

**Status:** Implementation foundation complete; manual IG demo validation still required.

### Tested search terms

The P01 CLI defaults to:

- `US Tech 100`
- `France 40`
- `Germany 40`
- `Gold`

Manual run results should be recorded here after using:

```powershell
trading-ig-assistant discover-products --watchlist --output .\watchlist.local.json
```

### Candidate counts

No live/demo discovery output has been pasted into this repository. Record sanitized counts only:

| Search term | Candidates returned | Classified products | Errors |
|---|---:|---:|---:|
| US Tech 100 | TODO | TODO | TODO |
| France 40 | TODO | TODO | TODO |
| Germany 40 | TODO | TODO | TODO |
| Gold | TODO | TODO | TODO |

### Suspected product types found

The service can classify candidates as:

- `barrier`: based on conservative text matches such as barrier or knock-out wording.
- `option`: based on option, call, put, or vanilla wording.
- `cash_or_dfb`: based on DFB/cash markers or common IG instrument types.
- `unknown`: fallback when classification is uncertain.

### Barrier visibility

TODO after manual demo API testing:

- Were Barrier products visible through market search?
- Did they appear as distinct EPICs?
- Did market details expose KO-related metadata?

### Option visibility

TODO after manual demo API testing:

- Were Option products visible through market search?
- Did they appear as distinct EPICs?
- Did market details expose strike, expiry, and call/put metadata?

### Useful fields to inspect

The P01 extractor looks for the following fields, but IG payload shape must be confirmed:

- KO level: `koLevel`, `knockoutLevel`, `knockOutLevel`, `barrierLevel`, `barrier`.
- Strike: `strike`, `strikePrice`, `exercisePrice`.
- Expiry: summary `expiry` or detail `expiry`.
- Direction: conservative text parsing for buy/sell/long/short/bull/bear/call/put.
- Min deal size: `minDealSize`, `minimumDealSize`, `minSize`.
- Currency: `currency`, `currencies`, `baseCurrency`, `quoteCurrency`.
- Market status: summary `marketStatus` or detail `marketStatus`/`status`.

### Unresolved questions

- Whether IG exposes Barrier and Option product metadata consistently across demo and live.
- Whether KO levels and strikes require a separate endpoint beyond market details.
- Whether any product constraints are account-specific.
- Whether dealing rules are sufficient to validate min/max/lot size locally.

### Next manual tests needed

- Run `discover-products --watchlist` against IG demo and record sanitized counts.
- Run GUI product discovery against the working live read-only profile and export the sanitized
  JSON report for local analysis.
- Confirm whether `/market-navigation` exposes the full relevant product universe for the selected
  account, or whether watchlists/search remain necessary complements.
- Avoid bulk-calling `/markets/{epic}` for every discovered product during manual tests; IG may
  reject long read-only scans with an invalid security token. Fetch detailed EPIC metadata later in
  targeted batches.
- Inspect whether Barrier/Option products are found for each watchlist instrument.
- Compare market summary versus market details payload shape.
- Confirm which fields identify KO level, strike, expiry, direction, min size, currency, and status.
- Keep order-related API testing out of P01; no order endpoints should be called.
