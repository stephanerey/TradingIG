# Findings

- `PaperOrderExecutionCoordinator` already owns atomic risk reservation, Paper authorization,
  idempotent submission and reservation release on failed submission.
- The proposal envelope needed to retain the exact immutable fill assumptions used at construction.
