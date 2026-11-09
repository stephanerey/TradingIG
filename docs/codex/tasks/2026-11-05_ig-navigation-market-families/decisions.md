# Decisions

- Preserve IG node IDs and names as an ordered breadcrumb loaded on demand.
- Bind one exact family node to one typed canonical underlying and one reference EPIC.
- Keep product EPIC and reference EPIC separate throughout the resolved contract.
- Reject nested competing family definitions rather than selecting the deepest one silently.
- Keep the generic node catalog for accounts where IG exposes it, but use the proven lazy category
  catalog on this DEMO profile. Category `code`, exact `underlyingName` and reference EPIC are all
  required; none substitutes for an unproven product-parent relation.
