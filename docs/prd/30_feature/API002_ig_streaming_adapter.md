# API002 — IG Streaming Adapter

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Original text is preserved; documented V1.2 changes govern current scope. No implementation or activation is implied.


> **PRD Policy:** **PROJECT (editable)** — Feature specification.\
**Last updated:** 2026-10-23


## Goal
Provide real-time updates for prices, positions, account/trade status through IG Streaming API / Lightstreamer.

## Non-goals
- Do not place orders through the streaming adapter.

## Responsibilities
- Start streaming session from authenticated REST context.
- Subscribe/unsubscribe to market price items.
- Subscribe to open positions/account/trade confirmations where available.
- Normalize quote updates to domain `Quote` events.
- Detect stale feed, disconnect, reconnect, heartbeat failure.
- Publish events to the application event bus.

## Candidate events
- `QuoteUpdated`
- `PositionUpdated`
- `AccountUpdated`
- `TradeStatusUpdated`
- `StreamConnected`
- `StreamDisconnected`
- `StreamStale`

## Constraints
- Streaming must not block UI thread.
- Reconnection must not duplicate subscriptions or events.
- Stale feed must disable pending-order triggers and live trade actions.

## Acceptance criteria
- Mock streaming adapter can drive chart updates.
- Stale-feed detection triggers within configured timeout.
- Reconnection preserves subscribed watchlist.

## Testing notes
- Unit-test event normalization and stale detection.
- Use mock Lightstreamer client in tests.

## V1.2 scope alignment

Preserve the working Lightstreamer/Qt integration. Apply F003 quality, cache-first, stale-state and gap-recovery requirements. Validate multi-account subscription capabilities before execution use.

Canonical requirements: [chapter 5](F001_ig_connection_and_settings.md), [chapter 6](F003_realtime_market_data_and_charts.md), [chapter 17](../10_architecture/domain_contracts.md).

## Verified implementation note — 2026-10-23

The current IG `PRICE:{account_id}:{epic}` subscription requires the Lightstreamer data adapter
`Pricing`. This was verified against DEMO with real read-only ticks. `MARKET:{epic}` returned
code 21 (`Invalid group`) and must not be used as a fallback on the current endpoint.

The chart path now also supports one deduplicated multi-item subscription containing several exact
`CHART:{epic}:1MINUTE` items. Incoming item identity is validated against the subscribed set before
normalization; unexpected or missing identity in a multi-item subscription is rejected. The
existing single-chart method remains a compatibility wrapper. This is offline-tested adapter
evidence only; it does not authorize a real subscription or connect the provisional Qt Scanner.
