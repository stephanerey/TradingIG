# Multi-chart streaming

## Objective

Allow one IG Lightstreamer adapter session to subscribe to several exact reference-chart EPICs for
the session-only multi-market Scanner foundation.

## Boundaries

- Read-only chart stream only; no REST history, ticket, broker mutation, AUTO or LIVE activation.
- Exact item identity and deterministic deduplication.
- Preserve the existing single-chart API.
