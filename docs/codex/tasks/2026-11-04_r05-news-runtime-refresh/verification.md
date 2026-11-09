# Verification

## Targeted

- Official runtime plus complete GUI-shell/source/context tests: `66 passed in 10.80s`.
- Targeted Ruff check: all checks passed.
- Targeted Ruff format check: all changed Python files formatted.

## Full offline suite

- `.venv\\Scripts\\python.exe -m pytest -q`: `300 passed in 14.07s`.
- Repository Ruff lint (`src`, `tests`, DEMO probe): all checks passed.
- `git diff --check`: passed; only pre-existing line-ending warnings were reported.

## Limitations

- Repository-wide format check still reports 11 pre-existing, unrelated files and was not applied
  to preserve local work.
- No live GUI network smoke was repeated; R05-SRC1 already proved both bounded public endpoints on
  2026-11-04, while this lot verifies the runtime with injected offline providers.
- No IG authentication, credential, Paper fill, DEMO/LIVE/AUTO order or broker mutation occurred.
