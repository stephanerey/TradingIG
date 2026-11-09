# Findings

- `CandleHistoryService` already keys session M1 observations by environment, account, reference
  EPIC and price basis; only explicit multi-market routing was missing.
- Multiple Barrier products can safely share one reference series while retaining distinct
  `selected_product_epic` values in their projected `ChartCandleSeries`.
