# Verification

## Targeted verification

- `pytest tests/unit/test_replay_metrics_service.py tests/unit/test_paper_broker.py tests/integration/test_r06_paper_flow.py tests/unit/test_ig_rest_adapter.py -q`
  - `34 passed in 0.18s`
- Ruff check and format check on the three new Python files: passed.

## Full verification

- `pytest -q`: `245 passed in 14.92s`.
- `ruff check src tests scripts/run_ig_demo_probe.py`: passed.
- `ruff format --check` on the three new Python files: passed.
- `python scripts/codex/generate_repo_map.py --write --root .`: regenerated successfully.
- `git diff --check`: passed; only pre-existing LF-to-CRLF warnings were reported.
