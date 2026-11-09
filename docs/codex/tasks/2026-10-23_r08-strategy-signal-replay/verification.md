# Verification

## Targeted verification

- Replay strategy/feed/metrics, indicators/scanner, PaperBroker, R06 integration and protected IG
  adapter: `61 passed in 0.25s`.
- Ruff check on the three affected Python files: passed.
- Ruff format check on the three affected Python files: passed.

## Full verification

- `pytest -q`: `258 passed in 13.39s`.
- `ruff check src tests scripts/run_ig_demo_probe.py`: passed.
- Ruff format check on the three affected Python files: passed.
- `python scripts/codex/generate_repo_map.py --write --root .`: regenerated successfully.
- `git diff --check`: passed; only pre-existing LF-to-CRLF warnings were reported.
