# Verification

- Targeted AUTO/risk/protected-adapter checks: `37 passed`.
- Full offline suite: `239 passed in 13.27s`.
- Repository lint for `src`, `tests` and the bounded DEMO script: all checks passed.
- Ruff format check for the three new Python files: passed after formatting two files.
- Protected current-capability test proves the normal IG adapter returns
  `CAPABILITY_UNSUPPORTED` to the AUTO gate.
- Source inspection test proves the readiness service imports no `IGRestAdapter` and contains no
  submit/create-position call.
- RepoMap regenerated successfully.
- `git diff --check`: no whitespace error; only pre-existing Windows LF→CRLF warnings.
- No network call, credential access, broker mutation, persistent storage, migration, dependency,
  GUI change or AUTO activation was performed by this lot.

Remaining acceptance gaps:

- No human-approved real whitelist, quota or AUTO activation decision.
- No quantitative replay/walk-forward evidence for an AUTO strategy.
- No signer/trust mechanism for acceptance evidence.
- Current IG order capabilities remain unsupported outside the consumed R07 probe.
