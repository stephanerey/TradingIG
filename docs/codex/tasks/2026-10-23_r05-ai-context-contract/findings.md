# Findings

- `ContextSignal`, `MacroRibbonState` and deterministic aggregation exist.
- `NewsProvider` and `EconomicCalendarProvider` files are empty placeholders.
- `MarketContextSnapshot`, typed AI output, model/prompt provenance and provider fallback are absent.
- The PRD requires deterministic numerical indicators outside widgets/LLMs; AI contributes
  structured context, sentiment, risk and explanation.
- The provider schema therefore excludes indicators, tickets and order instructions.
- Source IDs are accepted only when they refer to active, non-gray and non-expired signals from the
  deterministic `MacroRibbonState`; snapshot validity is clipped to cited-source validity.
- The safe fallback is explicit `UNAVAILABLE/UNKNOWN`, not a favorable neutral score. This is the
  conservative implementation of the PRD fallback requirement and BR-SCAN-003.
- Provider identity access can fail independently from analysis; both boundary failures degrade
  without leaking provider error text or fabricating context.
