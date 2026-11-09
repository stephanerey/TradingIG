# Decisions

- Source availability is data health, not a market recommendation; its score and confidence stay
  `None`, and its tags do not participate in risk/index/gold/event aggregation.
- Use the existing `QObject` + `QThread` pattern; add no dependency.
- Inject providers into `MainWindow`; unit tests default to no provider and never access the network.
- The production entry point supplies the two allowlisted official providers.
- Refresh at startup, every 15 minutes and on an explicit Tools action.
