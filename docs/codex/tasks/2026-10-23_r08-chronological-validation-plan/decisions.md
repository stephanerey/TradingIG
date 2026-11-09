# Decisions

- Use a separate replay-validation domain module instead of expanding execution-facing contracts.
- Require explicit integer point counts and steps; provide no ratio or strategy defaults.
- Use canonical JSON plus SHA-256 from the Python standard library.
- Represent partitions as immutable index/time metadata, not copied candle datasets.
