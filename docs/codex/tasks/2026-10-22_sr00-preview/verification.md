# Verification — SR00 preview

## Results

| Check | Result |
|---|---|
| `git branch --show-current` | PASS — `chore/sr41-upgrade` |
| `git rev-parse HEAD` | PASS — `512c16d59337d2b92bb475daecb96cc902eb00c0` |
| Official `git ls-remote`, shallow clone, remote/status/tag/version checks | PASS — source commit `596a681742e664dc9fdbbdc26783d62bba3f77f0`, tag `v4.1.0`, clean source, released 4.1.0 |
| Official installer `--help` | PASS — preview/write/upgrade/apply/restore modes identified |
| Official installer `--json` preview without write/upgrade | EXPECTED RED — exit 2, 136 operations, 13 conflicts, 4 preserved, dry run only |
| Content-bearing `--plan-out` outside target | PASS — plan captured for exact review; target unchanged |
| `python scripts/codex/verify_codex_pack.py` | PASS (legacy scope only) — old pack files present |
| `python scripts/codex/validate_skills.py` | FAIL — no legacy skill directories under `C:\Users\srey\.codex\skills` |
| Official `sr_post_install_check.py --root C:\Projects\TradingIG --json` from source | FAIL as expected — `ok: false`, required SR files/tools/version/knowledge mode missing |
| Project `.venv` creation | PASS — Python 3.12.6, ignored by Git; global Python unchanged |
| Local PyYAML installation/import | PASS — PyYAML 6.0.3 in `.venv` only |
| Resolved transaction plan validation | PASS — 149 operations, 0 conflicts, 4 preserved, 0 deletions; SHA-256 `2159a54a0c4b8d205637bd04e5168a9abd8d5990963b10c240f8c4c97818d92f` |
| Resolved plan applied to isolated target copy | PASS — official guarded transaction completed and created a restore journal |
| Official post-check on isolated installed copy | PASS — `ok: true`, no errors/warnings; all four subordinate commands exit 0 |
| Second official preview on isolated installed copy | PASS — 0 operations, 0 conflicts |
| Exact resolved plan applied to real target after approval | PASS — 149 operations, 0 conflicts, 4 preserved, 0 deletions |
| Real-target backup journal | PASS — `docs/codex/upgrade_backups/9bf66d10b02c4d2f99e62a8b00cc4626` |
| Official post-check on real target | PASS — `ok: true`, no errors/warnings; all subordinate commands exit 0 |
| Second official preview on real target | PASS — 0 operations, 0 conflicts |
| Planned AGENTS/SKILL_MAP prefix preservation | PASS — current content preserved before one appended managed block |
| `git diff --name-only -- src tests pyproject.toml` | PASS — empty |
| `git diff --check` | PASS |
| `python scripts/codex/safe_diff_summary.py` | PASS — no staged changes; only prior PRD work plus this new SR00 task directory |
| Final branch/HEAD/status | PASS — branch and HEAD unchanged; prior local changes preserved |

## Not run in SR00

- Application tests, Ruff, GUI smoke, imports, and market-data checks were deferred to the separate R00/R01 pass.
- No authenticated IG request, order action, application dependency change, commit, or branch operation.

