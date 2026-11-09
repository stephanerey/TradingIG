# Decisions

- The handoff is Paper-only and produces no fill, position, reservation or broker command.
- Scanner recommendation/provenance is copied from the exact `ScannerResult` cited by the
  directive; mismatches are rejected.
- The independent Risk Engine remains mandatory after proposal construction.
- Proposal, intent and underlying identities are explicit and non-empty. A current quote outside
  the directive entry zone invalidates the handoff instead of silently adjusting technical levels.

