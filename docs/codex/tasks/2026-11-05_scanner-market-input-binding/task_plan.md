# Scanner market input binding

## Objective

Prepare multi-market Scanner inputs from session candles only after an exact, provenance-bearing
product-to-canonical-market binding has been supplied.

## Boundaries

- No product-name or EPIC-pattern inference.
- No Qt, network, subscription, ticket, broker, order or AUTO path.
- Context and layered profile resolution reuse existing deterministic services.
