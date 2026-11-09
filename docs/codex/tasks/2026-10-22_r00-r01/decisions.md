# R00/R01 decisions

- Use the existing architecture and declared dependencies only.
- Keep all tests offline with fakes; no authenticated IG call.
- Do not alter live-trading protections or resolve settings inheritance.
- Preserve the already-correct historical-allowance behavior and only move the broader API allowance gate after local cache reads.
- Keep M1 revision state inside the existing aggregation service, keyed by epic, target interval, price basis, and bucket; do not introduce storage or schema changes.
- Reuse the existing Qt worker/thread pattern and discard stale generations instead of adding a new concurrency dependency.

