# Findings

- The local LIVE discovery report contains one unique TRADEABLE Barrier Buy/Sell pair for France
  40, Germany 40 and US Crude.
- Spot Gold exposes two TRADEABLE Buy/Sell pairs with the same names, expiry and instrument type but
  slightly different prices; the available bulk metadata does not identify a canonical pair.
- Human LIVE validation showed that the France 40 relationship resolves to
  `IX.D.CAC.IMF.IP`, but IG refuses its `CHART:...:1MINUTE` entitlement while continuing to send
  direct `PRICE` updates for the selected Barrier. Product identity and chart entitlement are
  therefore separate facts; the France binding is not evidence that its reference chart is
  streamable on every account.
- The GUI now falls back to session-only M1 candles built from the selected product's direct quotes
  after the selected reference `CHART` is explicitly denied. These candles keep the product EPIC
  and are not routed into the Scanner as verified underlying candles.
- Follow-up: the selected reference PRICE item was placed after all visible products, so it could
  fall outside the 20-item subscription limit. Its PRICE entitlement is consequently unproven;
  prioritizing it next to the selected product enables a bounded observation on the next session.
- The IG streaming reference states that MARKET was deprecated and scheduled for decommissioning
  on 2026-05-08: https://labs.ig.com/streaming-api-reference.html. The automatic probe has been
  removed from the UI path. The rejected isolated PRICE request still needs independent diagnosis.
- The option discovery snapshot repeats identical raw IG changes across distinct CALL/PUT products.
  Their instrument scope is unverified; the selector hides both option change columns for snapshot
  and live quotes, while preserving the underlying data and displaying an explanatory tooltip.
- Quote-derived MID highs/lows had been calculated by averaging independent bid and ask extrema,
  although those extrema can occur at different times. A delayed quote could also replace an
  already populated minute, and `PRICE.TIMESTAMP` was not parsed by the streaming adapter.
  Local fallback candles now retain extrema of observed MID updates, ignore out-of-order quotes and
  read the PRICE timestamp. This does not establish tick completeness or authorize Scanner input.
- The reference EPIC was observed TRADEABLE on a DEMO CFD account; the refused subscription was
  on a LIVE Barrier/Option account. An account-type or entitlement mismatch is plausible, but is
  not proven. Separately, the quote-candle accumulator used to key only by product EPIC, so a
  same-minute account/environment switch could carry a previous account's OHLC into the new one.
  Its state is now scoped by environment, account and product.
- The user selected `IX.D.CAC.IMF.IP` on DEMO CFD on 2026-11-06; the logs confirm actual IG
  `CHART:...:1MINUTE` updates. The same reference was refused on the LIVE Barrier/Option account;
  this is a difference in observed access, not proof of the reason. The exact CFD reference had
  no product binding and therefore could not be evaluated by the runtime Scanner even in DEMO.
  A self-binding now enables it, without changing the LIVE account's privileges.
- The grouped chart fallback checked only the permission error text; a PRICE permission error
  could therefore trigger a chart retry and replace the Scanner session router. It now requires
  a CHART group matching the current subscription size; unrelated errors remain visible.
- UI live quotes and Paper approvals survived account transitions, and queued events from a
  previous stream could arrive after a switch. Stream callbacks now carry a generation, while
  connection changes invalidate quote, chart, Scanner and Paper proposal state. An unsuccessful
  account switch no longer saves or displays the unconfirmed account and disconnects safely.
- Quote subscription DEBUG logging embedded the full account ID inside item names despite masking
  the separate account field. New log entries mask it; existing log files are not modified.
- Rebuilding the product table after a filter previously replaced session quotes with cached
  discovery snapshots. Rows now reuse received session quotes without refreshing ticket timestamps;
  tooltips distinguish snapshot and session values without claiming verified freshness.
- IG PRICE quotes carry an explicit `DELAY` flag in the existing raw fields. The GUI previously
  treated a newly received delayed quote as fresh, and the Paper manual-close path did not reject
  `fresh=False`. Explicitly delayed quotes now invalidate the Paper proposal, cannot trigger or
  manually close a Paper position, do not provide a position mark or Scanner spread. Missing or
  unrecognized delay markers remain unknown and retain existing behavior.
- Scanner spread used session quotes without a receipt-age limit. Paper session marks and manual
  closes trusted the quote's historical `fresh` flag indefinitely, including after a restore or
  connection change. Both now reuse the existing 30-second ticket window; a disconnected source
  invalidates Paper quotes without triggering fills. Paper view is refreshed on opening, but it has
  no periodic stale-data refresh while left open and can visibly age between events.

