# Decisions — SR00 preview

- Treat the target as a customized legacy Codex pack, not a fresh empty project.
- Do not infer SR completion from the branch name, the reconstructed PRD, or the legacy verifier.
- Use a project-local `.venv`; do not change global Python.
- Replace only the 12 reviewed generic method-pack conflicts with official 4.1.0 content and preserve their originals through the official transaction journal.
- Merge `PROJECT_PROFILE.yaml` by capability, preserve project/runtime commands, correct its invalid YAML quoting, and disable the irrelevant web Playwright runner for the native PyQt application.
- Preserve all PRD files, historical task memories, project-owned maps/state/design, application code, tests and packaging.
- Apply only the reviewed conflict-free plan through the official guarded `--apply-plan` path after exact human approval.
- Do not begin R00 or R01 until the real target post-install check passes.

