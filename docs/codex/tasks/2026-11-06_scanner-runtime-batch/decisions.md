# Decisions

- Add one UI-independent runtime assembler around the existing services instead of duplicating
  binding, profile, context or scoring logic in Qt.
- Isolate missing products, warmup and stale series per configured product.
- Preserve the current selected-product table as a temporary view of the batch result.
- Keep unbound products outside Scanner analysis while retaining discovery and Paper behavior.

