# Decisions

- Summarize closed `PaperPosition` objects instead of creating a second fill simulator.
- Use explicit latest-source and decision timestamps to make look-ahead testable.
- Keep every experiment tied to dataset, rules, strategy, code revision and fill model.
- Never mix currencies or experiment provenance in one comparison.
- Treat fixture metrics as implementation evidence only, never strategy performance evidence.
