# Findings

- `ContextSignal` and `MacroRibbonState` already provide the normalized downstream boundary.
- `news_provider.py` and `economic_calendar.py` are empty placeholders.
- API003 requires `MacroEvent`, `NewsItem`, `MarketContextFlag`, attribution, timestamps, importance,
  tags and explicit licensing/rights information.
- The PRD does not select a concrete provider or define provider-specific payload mappings.
- The existing `MacroContextService` already owns stale-to-gray behavior, so the source normalizer
  preserves validity timestamps rather than duplicating freshness policy.
- Multiple source URLs cannot be represented safely by the single downstream `source_url` field;
  multi-source flags therefore retain every source record ID in tags and leave that URL unset.
- Unknown usage rights are not a validation error because providers may report that state; the
  resulting signal is deliberately gray with no usable score or confidence.
