# Decisions

- Use only official HTTPS feeds with an explicit hostname allowlist.
- Use Python standard-library HTTP/XML; add no dependency.
- Store feed metadata only and declare `METADATA_ONLY` rights.
- Do not infer importance, severity, direction or score from headlines.
- Keep network collection outside the GUI and future scheduler until a non-blocking orchestration
  lot is authorized and verified.
- Treat provider/network/payload errors as explicit unavailable snapshots without leaking payloads.
