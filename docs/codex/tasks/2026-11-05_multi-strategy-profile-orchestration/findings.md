# Findings

- `MarketScannerInput` already supports one profile containing multiple strategies, but cannot
  retain distinct layered provenance per strategy.
- `build_scanner_preview` can safely evaluate a profile restricted to one technical strategy.
- `EVENT_DRIVEN` has a separate qualified-context engine and must not be manufactured by the
  closed-candle technical preview registry.

