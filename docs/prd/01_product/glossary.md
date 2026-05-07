# Glossary

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

| Term | Meaning |
|---|---|
| IG REST API | HTTP API used for authentication, snapshots, historical data, positions, orders, account history and similar request/response operations. |
| IG Streaming API | Lightstreamer-based API used for real-time price/account/position updates. |
| EPIC | IG market identifier used by APIs. |
| Barrier | Leveraged product with a knock-out level; risk and pricing depend on distance to the barrier/KO and product rules. |
| Knock-out / KO | Level at which a barrier product is knocked out/liquidated. |
| Stop | Exit condition intended to limit loss or secure gain. |
| Limit / target | Exit condition intended to take profit. |
| R | Initial risk unit: distance between entry and initial stop. Used for normalized trade management. |
| Software pending order | App-managed delayed entry condition; in MVP it alerts/prepares manual confirmation rather than blindly executing. |
| Protected trade | State where the stop has been moved to break-even or better. |
| Trailing trade | State where the stop follows price according to a deterministic rule. |
