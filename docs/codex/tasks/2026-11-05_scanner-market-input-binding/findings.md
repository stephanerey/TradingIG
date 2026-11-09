# Findings

- `MarketScannerService` already accepts independent inputs and resolved profiles.
- `ProductContextProjectionService` and `resolve_scanner_profiles_from_catalog` already provide the
  required context and layered settings; the missing boundary was strict identity composition.
- Cross-EPIC derivative/reference analysis keeps execution-price-scale verification false.
