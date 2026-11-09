# Verification

- `python -m pytest tests/unit/test_candle_history_service.py tests/unit/test_scanner_preview_ui.py tests/unit/test_ui_shell.py -q`
  - 67 passed.
- `python -m pytest -q`
  - 397 passed.
- Protected Paper/risk/DEMO-gate/IG-adapter regressions.
  - 38 passed.
- `python -m ruff check src tests`.
  - Passed.
- Targeted `ruff format --check` on the same files.
  - Passed.
- `git diff --check` on the changed Python/test files.
  - Passed.

No authenticated IG historical request, broker order or LIVE/AUTO action was executed. Native
Windows human observation of the session warmup remains useful but is not required to prove the
offline orchestration change.

