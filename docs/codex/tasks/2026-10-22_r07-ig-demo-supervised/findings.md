# Findings

- R06 prerequisite is complete with 187 offline tests.
- The current IG adapter exposes read-only capabilities and hard-blocks create/update/close/working-order methods with `LiveTradingDisabledError`.
- R07 acceptance requires sanitized DEMO evidence that cannot be manufactured from documentation or mocks.
- Human validation on 2026-10-22 authorizes authenticated IG DEMO read-only calls only; no broker mutation or LIVE call is authorized.
- On 2026-10-23 the local profile-presence check found a usable credential store, a DEMO identifier and a complete DEMO password/API-key pair.
- A single bounded login request to the explicit DEMO base URL returned HTTP 403 with `error.public-api.failure.stockbroking-not-supported`; the official IG session reference defines this as stockbroking not being supported for Public API users. No account listing was reached.
- The returned code is distinct from IG's invalid-credentials and invalid/disabled/restricted API-key codes. The evidence therefore points to the IG account type bound to the DEMO credentials, not to an application password validator or a LIVE/DEMO URL mix-up.
- Barrier/Option EPICs, order payloads, KO/size semantics and working-order support remain evidence questions by account and jurisdiction.
- The user later corrected the DEMO profile with IG and explicitly resumed validation.
- The explicit DEMO endpoint then authenticated successfully. Three accounts were returned; the
  active account was CFD/EUR, and available account types were CFD and PHYSICAL. No raw account
  identifier was recorded.
- Read-only state endpoints succeeded for open positions (0), working orders (0) and the last
  24 hours of activity (0). The activity endpoint required explicit bounded dates.
- A representative tradeable US Tech DEMO market exposed streaming metadata. With the required
  `Pricing` Lightstreamer data adapter, `PRICE` delivered its first tick and 50 updates in six
  seconds. The deprecated `MARKET` group was rejected with code 21 (`Invalid group`).
- Market-navigation endpoints remained unavailable (HTTP 404); search and categories remained
  usable.
- A representative Option EPIC returned metadata but was `EDITS_ONLY`, type `UNKNOWN`, with
  streaming prices unavailable. The known LIVE Barrier EPIC returned HTTP 500 on DEMO. These
  results do not prove DEMO order support for either family.
- The minimum-size US Tech CFD was rejected during planning because its conservative loss estimate
  exceeded the standard 1% risk budget. The selected replacement was the DEMO France 40 cash
  1-EUR CFD (`IX.D.CAC.IMF.IP`): TRADEABLE, EUR, size 0.5, minimum stop 4 points.
- The independent Risk Engine approved a 6-point initial stop with a conservative 4.25 EUR loss
  estimate against a 99.34 EUR budget. The exact plan was displayed before mutation.
- IG accepted and confirmed the minimum-size opening and the stop tightening to a 4.5-point
  distance. The first close transport used a native DELETE with a JSON body; IG treated its
  request body as null and rejected it with `validation.null-not-allowed.request`.
- Read-only reconciliation proved that exactly one matching position remained open. No blind
  retry was made. The compatibility transport (`POST` with `_method: DELETE`) then returned an
  accepted close confirmation, and a final positions query returned zero open positions.
- General CFD execution is not enabled by this evidence. The default REST adapter continues to
  hard-block mutations; only the separate single-use DEMO probe adapter can perform the exact
  authorized sequence. Barrier and Option execution remain `UNSUPPORTED`.
