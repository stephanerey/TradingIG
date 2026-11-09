---
name: codex-tradingig-supervised-demo-gate
description: >-
  Apply TradingIG's default-deny safety boundary when collecting authenticated IG DEMO evidence or changing supervised broker gates. Use it for DEMO capability discovery, account and product binding, sanitized evidence, reconciliation, confirmation snapshots and execution protections while LIVE remains forbidden.
---

# TradingIG supervised DEMO gate

Read `references/rules.md` before any authenticated IG DEMO check or supervised-execution change.

## Current authority

- The human authorization recorded on 2026-10-22 permits authenticated IG DEMO calls in read-only mode only.
- Do not create, update, cancel or close an order, position or working order under this authorization.
- Do not use a LIVE profile, LIVE account or LIVE endpoint, even for a read-only probe.
- Stop and request separate explicit authorization before any DEMO mutation or application change that could reach a mutating broker method.

## Non-negotiable boundary

- Select `IGEnvironment.DEMO` explicitly; never infer the environment from the current UI selection.
- Reject an unexpected LIVE session, account or endpoint immediately.
- Keep every execution capability `UNSUPPORTED` until sanitized evidence proves it for the exact DEMO account type and product family.
- Use credentials only through the existing credential store and in memory. Never print, log, persist or copy credentials, session tokens, API keys, raw account identifiers or full broker payloads.
- Limit authenticated checks to the smallest bounded read-only sequence needed for accounts, market metadata, positions or activity evidence.
- Record only sanitized timestamps, operation names, outcome/status classes, counts, non-sensitive product attributes and opaque account references.
- Treat missing credentials, incomplete identity, unexpected response shape and ambiguous broker state as a stop condition.
- Preserve `LiveTradingDisabledError` and all current DEMO/LIVE mutation hard blocks.

## Future mutation requirements

These rules do not grant mutation authority. If a later human decision explicitly authorizes a bounded DEMO mutation:

- require an immutable confirmation snapshot, current independent Risk Engine approval and an active kill switch;
- bind authorization and evidence to the exact DEMO account and product family;
- classify timeouts or ambiguous outcomes as `UNKNOWN`, reconcile from broker state and never retry blindly;
- prove create/update/close capabilities separately with sanitized evidence and keep unsupported combinations default-denied.

## Required closure

- Verify that the selected profile and base URL are DEMO before login.
- Close the authenticated session when the adapter supports it.
- Report read-only evidence separately from inferred or untested capabilities.
- Run protected order-method regressions after any application-code change.
- Leave R07 incomplete while order capabilities remain unverified or mutation authority is absent.
