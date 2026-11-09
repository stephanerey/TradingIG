# Verification

- Targeted baseline before mutation: `50 passed`.
- Ticket/UI/risk regression set after mutation: `55 passed`; final focused UI set: `44 passed`.
- Protected IG order-method regression: `13 passed`; `LiveTradingDisabledError` remains enforced.
- Full offline suite: `193 passed in 6.39s`.
- `ruff check src tests`: passed.
- Qt offscreen smoke: 960×600 viewport retained, ticket scrollable and disabled while
  only the chart-underlying quote exists. Screenshot:
  `.codex_artifacts/ui-paper-direct-quote-waiting-960x600.png` (local, untracked).
- Limitation: the offscreen Windows runner did not render widget text glyphs in the PNG;
  the exact explanatory label is therefore asserted by the functional regression test.
- Targeted `ruff format --check` for the new/changed ticket files: passed. Repository-wide format is not claimed because `tests/unit/test_ui_shell.py` contains pre-existing formatting drift outside the two import assertions added by this lot.
- Native Qt offscreen smoke at 960×600: viewport exact, minimum size hint 0×115, Paper preview approved for the deterministic fixture, product grid hidden while the scrollable ticket tab is active.
- Screenshot evidence: `.codex_artifacts/ui-paper-ticket-960x600.png` (local, untracked).
- SR pack and five project skills: valid.
- `git diff --check`: passed apart from pre-existing LF/CRLF notices.

No broker order, Paper fill, dependency, migration or persistent database was created by this lot.
The later quote correction was validated under the separately authorized R07 DEMO read-only pass.

## Direct-quote follow-up

- The selected product is placed first before the 20-item market quote cap.
- An underlying/chart quote cannot enable a ticket for a different selected product.
- The UI names the chart source and explicitly states that its price is not reused for the ticket.
- Focused ticket/UI regression set after this follow-up: `46 passed`.
- Full offline suite after this follow-up: `195 passed`.
- Protected IG REST order-method regression remains `13 passed`.
- `ruff check src tests`: passed.
- Before correction, bounded DEMO stream evidence: `PRICE` subscribed with zero updates;
  deprecated `MARKET` rejected with code 21 `Invalid group`.
- After correction, bounded DEMO `PRICE` evidence using data adapter `Pricing`: connected,
  subscribed, first tick received, 50 updates in six seconds, no stream error.
- Final focused streaming/UI/ticket regression set: `54 passed`.
- Final full offline suite: `195 passed`; protected IG order-method set: `13 passed`;
  `ruff check src tests`: passed.
- Native user validation after application restart: the selected US Tech 100 Barrier displayed its
  own recent direct bid/ask, the Paper evaluation button became enabled, the underlying chart
  continued separately and cached history remained available.
