# Verification

## Targeted verification

- Replay feed, metrics, indicators, PaperBroker, R06 integration and protected IG adapter:
  `45 passed in 0.22s`.
- Ruff check on the three affected Python files: passed.
- Ruff format check on the three affected Python files: passed.

## Full verification

- `pytest -q`: `250 passed in 13.25s`.
- `ruff check src tests scripts/run_ig_demo_probe.py`: passed.
- Ruff format check on the three affected Python files: passed.
- `python scripts/codex/generate_repo_map.py --write --root .`: regenerated successfully.
- `git diff --check`: passed; only pre-existing LF-to-CRLF warnings were reported.
