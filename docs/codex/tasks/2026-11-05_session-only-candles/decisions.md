# Decisions

- `D-SESSION-DATA-001`: until a reliable historical provider is selected, the desktop runtime uses
  only candles observed during the current application session.
- `D-SESSION-DATA-002`: M1 is the canonical streaming input; higher displayed timeframes are derived
  locally and therefore warm up more slowly.
- `D-SESSION-DATA-003`: insufficient technical history is an explicit quality limitation, not a
  Paper ticket veto. It cannot be converted into a favorable technical value or an AUTO signal.
- `D-SESSION-DATA-004`: sentiment/macro and manual AI context remain consultative and cannot replace
  deterministic technical indicators or bypass risk controls.
- The policy is reversible: dormant historical code and adapters are retained for a future bounded
  provider integration; no dependency or migration is added.

