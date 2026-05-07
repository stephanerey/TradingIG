# Logging and Errors

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

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
