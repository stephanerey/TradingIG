# Verification

## Research and format evidence

- Official Fed RSS documentation and live endpoint verified.
- Official ECB RSS documentation and live endpoint verified.
- Official BLS iCalendar documented, but the live automated request returned Access Denied and an
  anti-bot notice. The source was excluded without retry tricks or bypass.

## Targeted evidence

- Targeted source/context/AI/scanner/protected-order regressions.
  - First result: one diagnostic-message mismatch; the unsafe URL was already rejected.
  - Corrected result: `72 passed in 0.34s`.
- Ruff check on the four new/changed Python files.
  - Result: all checks passed.
- Ruff format check on the same files.
  - Result: four files already formatted.

## Bounded live smoke

- Fed monetary-policy RSS: `available`, 15 normalized metadata items, no reason codes.
- ECB press RSS: `available`, 15 normalized metadata items, no reason codes.
- No headline/article content, credentials, persistence, polling, AI classification or broker call.

## Full offline evidence

- `.venv\\Scripts\\python.exe -m pytest -q`
  - Result: `296 passed in 13.85s`.
- `.venv\\Scripts\\python.exe -m ruff check src tests scripts\\run_ig_demo_probe.py`
  with an isolated repository-local cache.
  - Result: all checks passed.
- Ruff format check on the four new/changed Python files.
  - Result: four files already formatted.

No authenticated IG access, credential, persistence, scheduler, Paper/DEMO/LIVE order or AUTO
activation was exercised by this lot.
