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
