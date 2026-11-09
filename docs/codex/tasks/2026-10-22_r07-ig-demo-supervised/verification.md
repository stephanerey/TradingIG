# Verification

- Project skill validation: `OK: 5 skill(s) valid`.
- Safe local presence check on 2026-10-23: configuration present; credential store available; DEMO identifier present; complete DEMO password/API-key pair present.
- One bounded request used `IGEnvironment.DEMO` and the official DEMO base URL. Result: HTTP 403, `error.public-api.failure.stockbroking-not-supported` during login; account retrieval was not attempted after the failure.
- No secret value, raw account identifier or broker payload was printed or persisted.
- No IG request was issued, no R07 application code or broker state was changed, and all order hard blocks remain intact.

## Resumed DEMO read-only evidence — 2026-10-23

- Environment object and base URL were explicitly checked as DEMO before every login.
- Login, account discovery, market search/details and logout succeeded.
- Sanitized account evidence: 3 accounts; active account CFD/EUR; raw identifiers omitted.
- `GET /positions` v2: success, 0 positions.
- `GET /workingorders` v2: success, 0 working orders.
- `GET /history/activity` v3 with a bounded 24-hour range: success, 0 activities.
- Representative DEMO `PRICE` stream with data adapter `Pricing`: subscribed, first update
  received, 50 updates in six seconds, no error; requested field names matched the documented
  top-of-book schema.
- Deprecated `MARKET` diagnostic: rejected with Lightstreamer code 21 `Invalid group`.
- No order, position or working-order mutation was issued. Sessions were closed after each
  bounded sequence and no credential, token, raw account identifier or broker payload was
  printed or persisted.

## Bounded DEMO mutation evidence — 2026-10-23

- Human scope: one DEMO-only, minimum-size TRADEABLE CFD position; confirm, tighten stop and close
  immediately. LIVE explicitly forbidden.
- Presented plan: France 40 cash 1-EUR CFD, BUY 0.5, initial stop distance 6 points, tightened
  distance 4.5 points, immediate close.
- Independent preflight: TRADEABLE, zero existing positions, conservative estimated loss 4.25 EUR,
  standard risk budget 99.34 EUR.
- Create: `ACCEPTED`, confirmed via immutable deal reference.
- Stop update: `ACCEPTED`, confirmed.
- Initial close: transport rejected with `validation.null-not-allowed.request`; no blind retry.
- Read-only reconciliation: exactly one matching DEMO position remained open.
- Reconciled close using the IG-compatible method override: `ACCEPTED`, reason `SUCCESS`.
- Final `GET /positions` v2: zero open positions and zero matching probe positions.
- No raw account identifier, credential, token or deal identifier was printed or persisted.
- Official references used: <https://labs.ig.com/reference/positions-otc.html>,
  <https://labs.ig.com/reference/positions-otc-deal-id.html>, and
  <https://labs.ig.com/reference/confirms-deal-reference.html>.

Capability result:

| Family / operation | Result |
|---|---|
| CFD read/account/market/stream | `SUPPORTED` by sanitized DEMO evidence |
| Bounded CFD create/confirm/update/close probe | Proven only through the single-use DEMO gate |
| Barrier execution | `UNSUPPORTED`; no representative DEMO execution evidence |
| Option execution | `UNSUPPORTED`; no representative DEMO execution evidence |
| Working orders | `UNSUPPORTED`; mutation remained hard-blocked |
| LIVE execution | `UNSUPPORTED` and forbidden |

R07 acceptance is complete with explicit unsupported capabilities. This does not activate general
DEMO execution, AUTO, or LIVE trading.
