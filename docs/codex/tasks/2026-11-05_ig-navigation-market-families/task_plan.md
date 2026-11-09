# IG navigation market families

## Objective

Model products like the IG web platform: lazy navigation hierarchy, exact product EPIC and an
explicit family node linking the product to one canonical underlying and reference price EPIC.

## Boundaries

- One navigation page per explicit browse action; no full-tree startup crawl.
- Navigation lineage is broker metadata, not a candle-history cache.
- No inference from display name or EPIC pattern.
- Unknown, missing or ambiguous family lineage fails closed.
- No network call in tests, UI rewrite, ticket, broker or order path.

## Verification

- Synthetic root/child/leaf navigation and exact breadcrumb.
- Explicit product → canonical underlying → reference EPIC resolution.
- Unknown, unvisited, duplicate and ambiguous lineage rejection.
- Protected/full tests, Ruff and format checks.
