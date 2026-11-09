# Multi-market session candles

## Objective

Retain independent in-memory M1 observations for several explicitly bound reference markets and
project them to Scanner timeframes without REST history or persisted cache.

## Boundaries

- Exact reference EPIC routing only.
- Session memory only; no network, disk cache, Qt scheduler, ticket, broker, order or AUTO path.
- Preserve revision, gap and account/environment isolation rules from the existing candle service.
