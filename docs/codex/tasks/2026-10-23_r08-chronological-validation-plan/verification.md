# Verification

## Targeted verification

- Replay validation/strategy/feed/metrics, indicators/scanner, PaperBroker, R06 integration and
  protected IG adapter: `67 passed in 0.28s`.
- Ruff check on the three new Python files: passed.
- Ruff format check on the three new Python files: passed.

## Structural checks

- New contracts are isolated in `domain/replay_validation.py`; no existing constructor or consumer
  signature changed.
- Plan objects contain fingerprints, parameters and index/time metadata only; no persistence,
  network, broker or partition-data access was added.

## Full verification

- `pytest -q`: `264 passed in 13.83s`.
- `ruff check src tests scripts/run_ig_demo_probe.py`: passed.
- Ruff format check on the three new Python files: passed.
- `python scripts/codex/generate_repo_map.py --write --root .`: regenerated successfully.
- `git diff --check`: passed; only pre-existing LF-to-CRLF warnings were reported.
