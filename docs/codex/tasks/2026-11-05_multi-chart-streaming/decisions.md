# Decisions

- Use one Lightstreamer multi-item chart subscription rather than one client per market.
- Parse and validate the item identity on every multi-market update.
- Keep `subscribe_chart` as a compatibility wrapper around `subscribe_charts`.
