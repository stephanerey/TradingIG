# F002 — Product Discovery and Barrier/Option Selection

> **PRD Policy:** **PROJECT (editable)** — Feature specification.  
**Last updated:** 2026-05-07


## Goal
Allow the user to choose one of the available IG Barrier or Option products/contracts for a selected market, rather than hardcoding one instrument.

## Non-goals
- Do not assume every product visible in the IG web platform is tradable through every API endpoint.
- Do not hide product constraints from the user.

## Requirements
- Search/select underlying markets such as US Tech 100, France 40, Germany 40, Spot Gold.
- Discover available product contracts where IG API exposes them.
- Display for each contract when available: name, EPIC, product type, expiry, direction, bid/ask, spread, KO/barrier level, min size, currency, status, margin/prime/cost fields, stop/limit distance constraints.
- Allow user to mark favorite products/contracts.
- Preserve selected product in ticket builder.
- If API support is incomplete, display an explicit `Unsupported / manual only` status.

## Constraints
- Product metadata may vary by account, jurisdiction, product type, and market status.
- The implementation must keep raw IG data sanitized and mapped to domain models.

## Acceptance criteria
- User can list candidate products for at least one configured market in demo or documented API spike.
- UI clearly shows why a product cannot be traded/selected.
- Selected product data is passed to risk/ticket builder without manual retyping.

## Testing notes
- Use recorded sanitized IG product snapshots.
- Unit-test mapping from API product metadata to `ProductContract`.
