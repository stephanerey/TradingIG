# Findings

- R07 is complete with one bounded DEMO CFD exception; it did not authorize AUTO.
- Existing `IGRestAdapter.capabilities()` still reports order and DEMO execution as unsupported.
- `PaperOrderExecutionCoordinator` is structurally paper-only and must remain unchanged.
- The PRD defines required AUTO controls but does not define approved production whitelists, quotas
  or an activation acceptance record. These values cannot be invented.
- A pure readiness gate can make those missing decisions explicit without creating an execution
  route.
- Safe start is deterministic: ANALYSIS mode, kill switch active and reconciliation incomplete.
- An activation is bound to both the canonical policy digest and runtime generation. A process
  restart therefore blocks readiness even if an old activation object is replayed.
- The current `IGRestAdapter` capability object causes `CAPABILITY_UNSUPPORTED`; there is no
  application path capable of satisfying the all-green synthetic test.
- The acceptance-evidence contract stores an immutable SHA-256 digest, but no signer/trust model is
  selected or claimed. That external/human decision remains open.
