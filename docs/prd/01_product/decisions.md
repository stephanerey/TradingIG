# Decisions

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

Use this as an ADR-light log.

## Decisions
- **ID:** D-001
  - **Date:** 2026-05-07
  - **Context:** The product can become dangerous if it tries to trade autonomously before API support and risk controls are proven.
  - **Decision:** MVP is a disciplined assistant with manual confirmation by default. Fully automatic live execution is out of MVP scope.
  - **Alternatives:** Full robot from day one; rejected because API/product constraints and risk-management logic are not yet verified.
  - **Consequences:** Build adapters and state machines now, but gate live order execution behind explicit settings and tests.

- **ID:** D-002
  - **Date:** 2026-05-07
  - **Context:** IG Barriers/Options may not support native delayed orders in the same way the user wants to trade them from the platform.
  - **Decision:** Implement software pending orders: the app monitors trigger conditions and alerts/prepares the user to place/confirm the ticket manually.
  - **Alternatives:** Only use IG native working orders; rejected until product support is proven for the target products.
  - **Consequences:** Need robust trigger states, validation, expiry, cooldown, and logging.

- **ID:** D-003
  - **Date:** 2026-05-07
  - **Context:** Credentials will be entered through a configuration screen.
  - **Decision:** Credentials MUST be stored in OS keyring or equivalent encrypted storage, not plaintext config files.
  - **Alternatives:** `.env` or YAML config with password/API key; rejected for live account safety.
  - **Consequences:** Implement a credential provider abstraction and redaction tests.

- **ID:** D-004
  - **Date:** 2026-05-07
  - **Context:** The user wants a chart close to IG visual workflow.
  - **Decision:** The app will implement an IG-like candlestick chart with trading overlays, not a generic line chart.
  - **Alternatives:** rely only on IG web UI; rejected because software pending order and stop management need integrated overlays.
  - **Consequences:** Chart model and UI must support candle aggregation, overlay layers, and real-time updates.
