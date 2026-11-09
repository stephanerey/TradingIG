# F002 — Product Discovery and Barrier/Option Selection

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Original text is preserved; documented V1.2 changes govern current scope. No implementation or activation is implied.


> **PRD Policy:** **PROJECT (editable)** — Feature specification.\
**Last updated:** 2026-10-22


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

## V1.2 scope alignment

Include CFD and Barriers/Options per account and verified product capability. Source/execution mappings remain explicit; unsupported features stay visibly blocked. No inferred IG support.

Canonical requirements: [chapter 4](../10_architecture/overview.md), [chapter 5](F001_ig_connection_and_settings.md), [chapter 8](F006_ticket_builder_and_risk_engine.md).

## IG-style navigation implementation evidence — 2026-11-05

The broker-independent catalog now mirrors the observable IG interaction without crawling the
whole tree: root and child pages are loaded only when explicitly requested, and each loaded market
retains the exact ordered IG node breadcrumb. A separate explicit family definition binds one IG
node to one typed canonical underlying and one reference-price EPIC. The selected tradable product
retains its distinct EPIC for quote/ticket use. Missing, unknown or ambiguous ancestry is rejected;
names and EPIC patterns are not treated as proof. Tests use synthetic pages only, so real-account
node IDs, reference EPICs and UI wiring remain pending validation.

The bounded DEMO check on 2026-11-05 found that both public navigation route spellings return 404
for the active profile. IG's category route is available instead and returns category `code` plus
reference instruments carrying exact `underlyingName`, EPIC, lot size and scale. The adapter now
accepts this observed schema and a lazy category catalog validates configured references against
it. Five expected reference candidates were observed as tradeable, but IG exposed no public link
from a Barrier/Option EPIC to that parent in this sequence. Such a relation therefore remains an
explicit mapping, never a name-based inference.

The provisional runtime chart resolver now follows that boundary as well. Cached discovery rows
and targeted market search results are never ranked by display-name similarity to infer a parent.
An exact product-EPIC override is preferred; without an explicit mapping, the selected product
remains isolated as its own chart source. The observed US Tech, France 40, Germany 40 and US Crude
Barrier Buy/Sell EPICs now have exact default overrides to their validated reference EPICs. The
three additional pairs come from the local LIVE discovery evidence dated 2026-11-06. Spot Gold
remains unbound because that same evidence exposes two indistinguishable pairs. Legacy user
configuration keys by display name remain readable for compatibility but are no longer generated
as defaults. A binding proves the configured product/reference relationship, not the account's
Lightstreamer `CHART` entitlement: the first LIVE France 40 check resolved the exact reference but
IG denied its chart stream. Direct product-price fallback candles therefore remain product-scoped
and cannot satisfy the Scanner's verified-reference input contract.

Exact product bindings are now persisted separately from the legacy chart override map. Each entry
stores the product EPIC, a member of the closed canonical-underlying vocabulary, the exact reference
EPIC and non-empty provenance. Duplicate products and unsupported canonical values are rejected.
The Settings round trip preserves these bindings without exposing the deferred GUI editor.

## V1.2 traceability

[Chapter 4](../10_architecture/overview.md) · [Chapter 5](F001_ig_connection_and_settings.md) · [Chapter 8](F006_ticket_builder_and_risk_engine.md) · [Acceptance matrix](../90_quality/acceptance_matrix.md) · [Definition of Done](../90_quality/definition_of_done.md). Criteria are specifications, not passed test results.
