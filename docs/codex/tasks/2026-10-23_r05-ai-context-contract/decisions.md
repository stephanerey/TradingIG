# Decisions

- Keep technical indicator calculation deterministic and outside the AI boundary.
- Accept JSON-like mappings from providers and validate them before creating domain objects.
- Treat fallback as unavailable/unknown with zero usable confidence, never as favorable context.
- Derive model identity from the provider boundary, not from provider-generated content.
