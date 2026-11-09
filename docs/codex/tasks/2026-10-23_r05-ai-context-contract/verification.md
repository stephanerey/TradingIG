# Verification

## Targeted evidence

- `python -m pytest tests/unit/test_ai_context_service.py tests/unit/test_macro_context_service.py tests/unit/test_setup_scoring_service.py tests/unit/test_indicator_service.py tests/unit/test_ig_rest_adapter.py tests/unit/test_paper_broker.py -q`
  - Result: `56 passed in 0.27s`.
- `python -m ruff check` on the new domain, service and tests with an isolated cache.
  - Result: all checks passed.
- `python -m ruff format --check` on the same files.
  - Result: all files already formatted.

## Full offline evidence

- `.venv\\Scripts\\python.exe -m pytest -q`
  - Result: `274 passed in 15.80s`.
- `.venv\\Scripts\\python.exe -m ruff check src tests scripts\\run_ig_demo_probe.py`
  with an isolated repository-local cache.
  - Result: all checks passed.
- `.venv\\Scripts\\python.exe -m ruff format --check` on the three new Python files.
  - Result: three files already formatted.

No network, external AI provider, authenticated IG call, Paper/DEMO/LIVE order or AUTO activation
was exercised by this lot.
