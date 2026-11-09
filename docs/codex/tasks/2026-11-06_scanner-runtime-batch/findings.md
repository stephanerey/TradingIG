# Findings

- The session router, exact binding preparer and multi-market scoring core already exist independently.
- The Qt refresh path still scores only the visible chart series directly and does not use the batch.
- Only the two explicitly validated US Tech Barrier bindings are configured by default; the other
  reference streams must not be projected onto products without an exact binding.
- The LIVE permission fallback still provides the selected US Tech reference series, so both exact
  US Tech Barrier bindings can share that canonical series even when the wider Scanner stream is
  unavailable. Missing configured products and warmup remain isolated failures.

