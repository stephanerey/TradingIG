# Task plan — SR00 preview

## Objective

Verify the current TradingIG method-pack state and the official SR 4.1 source, run only the official read-only migration preview, classify proposed changes/customizations/conflicts, and stop before installation, R00, or application code changes.

## Baseline

- Repository: `C:\Projects\TradingIG`
- Branch: `chore/sr41-upgrade`
- HEAD: `512c16d59337d2b92bb475daecb96cc902eb00c0`
- Existing PRD consolidation changes are uncommitted and must be preserved.

## Skills

The legacy method skills named in `docs/codex/SKILL_MAP.md` are not installed in this session and are not used as if available. The task follows `AGENTS.md`, the repository workflow, and the official SR preview tool directly. No application-development skill is applicable because SR00 must stop before R00/R01.

## Plan

1. Inspect repository state and existing SR markers without mutation.
2. Verify the official source URL, commit, Git state, version, and release status.
3. Identify a project-local Python interpreter if present; otherwise record the limitation and use an available interpreter only for the dependency-free preview.
4. Run `install_codex_pack.py` in preview mode only (`--json`, without `--write` or `--upgrade`).
5. Classify exact create/update/preserve/remove/conflict actions and local customizations.
6. Record verification, recheck Git scope, and stop before installation and application work.

## Allowed changes

Only these five SR00 evidence files under this task directory. No edits to existing documentation, `AGENTS.md`, configuration, `src/`, `tests/`, or `pyproject.toml`; no deletion, branch change, commit, dependency installation, authenticated IG call, or application coding.

## Outcome

Preview completed with unresolved conflicts. SR00 remains incomplete and work stopped before installation, R00, and R01.

## Follow-up authorization — 2026-10-22

The user explicitly requested treatment of the five remaining steps: create a project Python environment with PyYAML, resolve the preview conflicts conservatively, regenerate the exact preview for human approval, then—only after that approval—install/post-check SR 4.1 and execute R00 followed by R01. The current subphase remains preparation-only until the regenerated plan is approved.

Current gate: the regenerated 149-operation plan has zero conflicts and passed installation/post-check/idempotence on an isolated copy. Exact human approval is pending before real-target application.

