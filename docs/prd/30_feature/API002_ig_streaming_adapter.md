# API002 — IG Streaming Adapter

> **PRD Policy:** **PROJECT (editable)** — Feature specification.  
**Last updated:** 2026-05-07


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
