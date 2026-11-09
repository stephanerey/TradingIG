# Logging and Errors

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Original text is preserved; documented V1.2 changes govern current scope. No implementation or activation is implied.


> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-10-22

## Goal
Make failures visible and diagnosable without leaking secrets or allowing unsafe trading.

## Logging rules
- Use structured logs where practical.
- Include event IDs for trade lifecycle actions.
- Redact username, password, API key, CST/X-SECURITY tokens, account IDs where sensitive, and authorization headers.
- Never log full HTTP request headers.
- Never log raw credential fields from UI.

## Error classes
- `ConnectionError`
- `AuthenticationError`
- `SessionExpiredError`
- `MarketClosedError`
- `StaleDataError`
- `OrderRejectedError`
- `RiskValidationError`
- `UnsupportedProductError`
- `ProviderUnavailableError`

## Safety behavior
- If streaming is stale, disable new trade actions and pending-order triggers.
- If REST session is invalid, disable execution/update actions.
- If order status is unknown, freeze automation and require user review.

## Acceptance criteria
- Errors shown to user contain action-oriented messages.
- Logs contain enough context to debug without secrets.
- Risk validation errors state which rule failed.

## Testing notes
- Add redaction unit tests with representative secret patterns.

## V1.2 scope alignment

Use structured UTC events, correlation/causation IDs, sanitized rotating logs and explicit UNKNOWN/UNSUPPORTED. Timeout is not proof of rejection: reconcile before resubmission. Local critical alerts remain available when delivery fails.

Canonical requirements: [chapter 9](../30_feature/F007_software_pending_orders.md), [chapter 13](../30_feature/F009_trade_journal_and_analytics.md), [chapter 15](../30_feature/F013_alerts_diagnostics_and_resilience.md), [chapter 17](domain_contracts.md).
