# Decisions

- Reuse the canonical M1 store instead of creating a second OHLC implementation.
- Store one reference series and project it separately for every explicitly bound product.
- Reject unbound stream EPICs rather than creating an implicit market.
