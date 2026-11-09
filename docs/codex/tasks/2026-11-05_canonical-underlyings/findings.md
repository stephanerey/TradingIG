# Findings

- Market profile keys were strict non-empty strings but did not restrict the accepted vocabulary.
- The existing explicit mapping contract exposes `InstrumentMapping.underlying_id`; no runtime
  registry data for the five real markets is currently populated.
- A typed ID is reversible at the JSON boundary because enum values remain the approved strings.

