# Findings

- The Qt shell already uses worker objects moved to `QThread` for IG connection, discovery and
  price history.
- The macro ribbon accepts normalized `ContextSignal` records and can expose data health without
  changing aggregate market direction when no directional tags or scores are supplied.
- Existing `MainWindow()` tests require a network-disabled default; the production entry point is
  the correct composition root for concrete official providers.
