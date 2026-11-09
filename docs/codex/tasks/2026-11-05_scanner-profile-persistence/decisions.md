# Decisions

- Human validation: account patches use the IG account ID, strategy patches use `StrategyId`,
  and market patches use a canonical underlying rather than a Barrier/Option EPIC.
- Persist override values with explicit type tags; JSON number coercion is not accepted.
- Reject malformed persisted profile configuration instead of silently applying defaults.
- Keep the catalog read-only in the current GUI; the dedicated GUI redesign remains later work.

