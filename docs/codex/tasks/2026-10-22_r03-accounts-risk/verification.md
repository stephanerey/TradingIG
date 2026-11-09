# Verification

| Check | Result |
|---|---|
| Project domain skill validation | PASS — `OK: 1 skill(s) valid` |
| Targeted account/risk/protected-order tests | PASS — 25 tests |
| Full offline suite | PASS — 122 tests |
| `ruff check src tests` | PASS |
| Targeted `ruff format --check` | PASS — 5 files |
| SR 4.1 post-install check | PASS — no errors or warnings |
| RepoMap refresh | PASS — includes the R03 domain module |

Covered: account-switch mismatch, 1%/3% defaults, missing FX/exposure, unconfirmed account, financial/market vetoes, shared underlying limits and atomic concurrent reservations.

Limits: no authenticated broker call, order, persistence migration, product-specific sizing formula or execution activation. Repository-wide format check still reports unrelated pre-existing formatting differences; modified R03 source/tests pass the targeted check.
