# Findings

- `ReplayDataset` already validates closed UTC candles, strict chronology and source provenance.
- Experiment provenance currently names dataset ID/version but does not prove immutable content;
  a deterministic content digest closes that evidence gap without persistence.
- The PRD requires chronological train/validation/test and walk-forward validation but defines no
  split ratios or window sizes, so defaults would be invented business choices.
- Rolling folds may leave a tail shorter than the requested full window; it must remain explicit.
- Plan parameters must be retained even when only one rolling fold fits; inferring the requested
  step from generated windows would lose experiment provenance.
- New contracts live in a separate module and do not modify existing replay consumer signatures.
