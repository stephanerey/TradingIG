# R07 IG demo and supervised gate

## Objective

Collect sanitized, representative IG DEMO capability evidence and validate a supervised execution coordinator without opening any LIVE capability.

## Smallest sufficient approach

- Keep every execution capability `UNSUPPORTED` until representative DEMO evidence proves it for the exact account/product family.
- Separate read-only discovery from any DEMO create/update/close probe.
- Require a visible immutable confirmation snapshot and current Risk Engine approval before a supervised DEMO command.
- On timeout/ambiguity, enter `UNKNOWN`, reconcile activity/positions/confirmations and never resubmit blindly.
- Record only sanitized request/response shape, capability result, timestamp and reason; never credentials, tokens or real account identifiers.

## Existing authority boundary

Human validation on 2026-10-22 authorizes authenticated IG DEMO read-only calls only. It does not authorize any DEMO order mutation, any LIVE call or modifications to `LiveTradingDisabledError`.

## Validated domain skill

`codex-tradingig-supervised-demo-gate` enforces:

- DEMO-only evidence; LIVE accounts and endpoints always rejected.
- explicit human authorization immediately before any DEMO create/update/close probe;
- read-only discovery first and minimum representative DEMO action only when separately authorized;
- exact account/product capability binding and default-deny fallback;
- immutable confirmation fields, fresh risk check, kill-switch and account isolation;
- `UNKNOWN` plus reconciliation on ambiguous response, never automatic retry;
- strict evidence sanitization and preservation of LIVE hard blocks.

## Gate

The skill and read-only DEMO scope are validated. The local DEMO profile is incomplete, so the next allowed action is user configuration of that profile. DEMO order creation/update/closure still requires a separate explicit authorization.

## Resumption — 2026-10-23

The user reports that IG corrected the DEMO account issue and explicitly asks to resume
validation. The resumed pass remains read-only and DEMO-only: verify the configured profile,
login endpoint, account discovery and a minimal representative market metadata sequence using
the existing credential store. Close the session and record only sanitized counts/statuses.
Order, position and working-order mutations remain outside the authorization.
