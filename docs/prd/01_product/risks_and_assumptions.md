# Risks and Assumptions

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

## Assumptions
- A1: IG demo access can be enabled with the same email as the live account and a generated API key.
- A2: IG REST and Streaming APIs provide enough market/account data to reconstruct the target workflow.
- A3: Some Barrier/Option operations may not support all order workflows exposed in the web UI; the app must detect support and fall back to manual assisted mode.
- A4: The user will initially run the app locally on a trusted desktop machine.
- A5: The MVP should first be validated in demo mode or dry-run mode before any live execution.

## Risks
| Risk | Impact | Likelihood | Mitigation | Owner |
|---|---|---|---|---|
| R-01 | IG API does not expose all Barrier/Option product data needed | High | Medium | P00 API spike; support read-only/manual workflow if needed | Dev |
| R-02 | IG rejects order/update requests due to market/product constraints | High | Medium | Validate market status, min size, distance rules, API error handling; never assume execution | Dev |
| R-03 | Credentials leaked through config/logs | Critical | Low/Medium | OS keyring, masking, redaction tests, no plaintext secrets | Dev |
| R-04 | Streaming feed disconnects or becomes stale | High | Medium | Heartbeat, stale-data warnings, REST fallback snapshot, disable trading actions while stale | Dev |
| R-05 | Software pending order triggers on a spike or wick | Medium | Medium | Confirmation rules: close-of-candle, hold time, tolerance, cooldown | Dev |
| R-06 | User overtrades after a win | Medium | High | Exposure rules, daily trade limit, warning after winning trade, journal prompt | Product |
| R-07 | News/macro module produces misleading context | Medium | Medium | Source attribution, confidence tags, no automatic trade solely from news | Product/Dev |
| R-08 | Live mode causes financial loss due to bug or latency | Critical | Medium | Demo-first, dry-run, manual confirmation, kill switch, max-loss guard | Product/Dev |

## Open questions
- Q1: Which exact IG EPICs represent the preferred Barrier/Option products for US Tech 100, France 40, Germany 40, and Spot Gold?
- Q2: Does the IG API support listing and opening the same Barrier/Option contracts visible in the web platform for the user account jurisdiction?
- Q3: Can `/workingorders` be used for the target products, or must delayed entry remain software/manual assisted?
- Q4: Which news/economic calendar provider will be used first: IG calendar, public RSS/API, paid provider, or manual event import?
- Q5: Should live mode initially be restricted to manual confirmation only even if API execution is technically possible?
