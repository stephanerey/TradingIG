# Decisions

- No capability is inferred from the IG web UI, PRD, product name or mocked response.
- R07 cannot weaken LIVE protection and cannot use a LIVE account.
- An authenticated read-only DEMO check is not implicit permission for a DEMO order mutation.
- Ambiguous order outcomes require reconciliation and forbid automatic resubmission.
- Successful DEMO read-only access reopens R07 but does not grant or imply mutation capability.
- Keep Barrière and Option execution capabilities `UNSUPPORTED` after inconclusive read-only
  metadata; do not generalize from the working CFD market stream.
- On 2026-10-23 the user explicitly authorized one DEMO-only bounded CFD probe at minimum size:
  create, confirm, tighten stop and close immediately. LIVE remains forbidden. The exact product,
  size and levels must be presented before mutation.
- Keep the main `IGRestAdapter` mutation methods hard-blocked. The authorization is implemented by
  a separate single-use DEMO-only adapter with immutable account/product/size binding and operation
  consumption before network dispatch.
- Treat the rejected native DELETE as a known transport incompatibility, not an ambiguous broker
  fill. Permit a recovery close only after a read-only query proves the exact position still exists.
- Use IG's compatibility method override for body-bearing closes. Never resubmit create/update/close
  after a timeout without reconciliation.
