# R00/R01 verification

| Check | Result |
|---|---|
| Project `.venv` / Python | PASS — CPython 3.12.6, isolated from global environment |
| `python -m pip check` | PASS — no broken requirements |
| Baseline full `pytest -q` | PASS — 102 tests |
| Final full `pytest -q` | PASS — 104 tests |
| Focused R01 regressions | PASS — 4 tests: cache, barrier chart-source cache, M1→M5 revisions, Qt responsiveness |
| `ruff check` on four changed application/test files | PASS |
| `ruff check src tests` baseline | PASS |
| Offline Qt GUI smoke | PASS — window shown and event processing completed, no history worker left running |
| Console entry point and module CLI `--help` | PASS |
| Final SR 4.1 post-install check | PASS — `ok: true`, no errors/warnings, four subordinate checks passed |
| `git diff --check` | PASS (line-ending notices only on pre-existing documentation/SR files) |
| User-operated LIVE smoke | PASS (user-reported) — connection succeeded and crude-oil candles arrived; Codex did not handle credentials or issue authenticated requests |

## Known limitations

- Repository-wide Ruff is red in pre-existing/generated SR utility scripts; this is outside R01.
- Formatting checks remain red on pre-existing application and SR files. The changed aggregation file was already among files Ruff would reformat; no unrelated formatting sweep was made.
- The standalone skill validator is not a green gate for the official installed pack: its default path is absent at repository root, and the explicit SR skill path reports six official descriptions below its local length rule. The official SR post-install check remains fully green; those method files were not customized.
- GUI verification was offline and headless. No authenticated IG history endpoint, Lightstreamer session, or live order path was exercised.
- No R02 work was started.

