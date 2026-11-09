# Findings — SR00 preview

## Verdict

SR00 is not yet installed in the real target. The initial preview exposed 13 conflicts; a reviewed, conflict-resolved transactional plan now has 149 operations and zero conflicts. Applying that plan to a temporary copy produced a fully green SR 4.1 post-check and an idempotent second preview with zero operations. Human approval of the exact resolved plan is the remaining gate before real installation.

## Repository baseline

- Target: `C:\Projects\TradingIG`
- Branch: `chore/sr41-upgrade`
- HEAD: `512c16d59337d2b92bb475daecb96cc902eb00c0`
- The pre-existing PRD consolidation remains uncommitted and unchanged.
- No staged change, branch switch, commit, deletion, application edit, or authenticated IG action occurred.

## Existing method installation

None of the SR 4.1 markers `docs/codex/SR_PACK_VERSION.json`, `docs/codex/SR_METHOD.md`, `docs/codex/SR_LOTS.yaml`, or `scripts/codex/sr_post_install_check.py` exists in the target.

The legacy verifier reports only that its old pack files are present. Its skill validator finds no skill directories in `C:\Users\srey\.codex\skills`. The official post-install checker reports `ok: false`, missing required SR files, missing audit commands, invalid/missing version metadata, and no valid knowledge mode. This proves that the branch name and PRD are not an installed SR 4.1 environment.

## Official source

- Repository: `https://github.com/syl2042/Aurora_SR_method_codex_pack.git`
- Remote `main` and cloned HEAD: `596a681742e664dc9fdbbdc26783d62bba3f77f0`
- Tag at HEAD: `v4.1.0`
- Commit date/message: `2026-09-24T17:24:14Z — Release SR 4.1.0: lean harness and token optimization`
- `core/SR_PACK_VERSION.json`: version `4.1.0`, `release_status: released`, `released_at: 2026-09-24`
- Clone state: clean `main...origin/main`
- Temporary source: `C:\Users\srey\AppData\Local\Temp\TradingIG-SR00-7c2215c6e5f245de8d79976835fb23ff`

## Project Python environment

A project-local `.venv` was created from Python 3.12.6 and remains ignored by Git. PyYAML 6.0.3 was installed only in that venv to run the official profile reconciliation. No global interpreter or application dependency declaration was changed.

## Initial official preview result

Command shape:

~~~powershell
C:\Python312\python.exe <official-source>\scripts\install_codex_pack.py --source <official-source> --target C:\Projects\TradingIG --json
~~~

Result: exit 2, explicit `dry run: no files written`.

- 136 planned operations: 132 creations, 2 append-only managed-block integrations, 1 `.gitignore` addition, and 1 managed-state creation.
- 13 conflicts, excluded from operations and therefore not overwritten by the preview plan.
- 4 project-owned files explicitly preserved.
- 0 deletions and 0 obsolete-file removals.
- No operation under `src/`, `tests/`, or `pyproject.toml`.
- The full content-bearing plan was saved outside the target at `tradingig_sr00_preview_plan.json` in the temporary source directory.

### Existing files that the plan would change

| Path | Classification | Exact treatment |
|---|---|---|
| `AGENTS.md` | unmanaged | Preserve all 78 current lines and append one official SR 4.1 managed block; resulting file 91 lines. |
| `docs/codex/SKILL_MAP.md` | unmanaged | Preserve all 48 current lines and append one official SR 4.1 managed block; resulting file 75 lines. |
| `.gitignore` | managed_modified | Append the comment `# SR local authentication state` and `.playwright/.auth/`; 33 to 35 lines. |
| `docs/codex/SR_MANAGED_STATE.json` | managed_state | Create a 143-line managed fingerprint registry. |

The preview content confirms byte-for-byte preservation of the current prefix of both `AGENTS.md` and `SKILL_MAP.md` before the new managed block.

### Files explicitly preserved

- `docs/codex/CODEBASE_MAP.generated.md`
- `docs/codex/CODEBASE_MAP.md`
- `docs/CURRENT_STATE.md`
- `DESIGN.md`

All existing PRD files and task memories are outside the installer's mutation list and remain untouched.

### Conflicts requiring review before any upgrade

| Path | Installer reason |
|---|---|
| `docs/adr/ADR_TEMPLATE.md` | unknown or locally customized pack file |
| `docs/codex/PROJECT_PROFILE.yaml` | PyYAML unavailable: cannot safely merge the existing profile |
| `docs/codex/REPO_MAP_POLICY.md` | unknown or locally customized pack file |
| `docs/codex/TOKEN_OPTIMIZATION.md` | unknown or locally customized pack file |
| `docs/codex/WORKFLOW_CODEX.md` | unknown or locally customized pack file |
| `docs/codex/prompts/00_install_codex_environment.md` | unknown or locally customized pack file |
| `scripts/codex/validate_skills.py` | unknown or locally customized pack file |
| `scripts/codex/verify_codex_pack.py` | unknown or locally customized pack file |
| `docs/codex/tasks/_TEMPLATE/decisions.md` | unknown or locally customized pack file |
| `docs/codex/tasks/_TEMPLATE/findings.md` | unknown or locally customized pack file |
| `docs/codex/tasks/_TEMPLATE/progress.md` | unknown or locally customized pack file |
| `docs/codex/tasks/_TEMPLATE/task_plan.md` | unknown or locally customized pack file |
| `docs/codex/tasks/_TEMPLATE/verification.md` | unknown or locally customized pack file |

The 12 unknown/customized files differ materially from the official source. Source-versus-target diff sizes range from small template changes to large method rewrites; notably `WORKFLOW_CODEX.md` is +9/-88, `REPO_MAP_POLICY.md` +4/-41, `validate_skills.py` +48/-84, `verify_codex_pack.py` +52/-35, and the task-plan template +134/-21. These are not safe blind replacements.

The profile conflict is environmental and semantic:

- The official installer refuses to merge `PROJECT_PROFILE.yaml` without PyYAML.
- Its intended reconciliation preserves existing project scalars/lists unless method-owned, adds missing SR sections, removes legacy `codex.require_planning_with_files` and `codex.require_review_diff`, and replaces the method-skill list with the SR 4.1 catalog.
- The official default also adds web-oriented `ui_validation` settings (Node/Playwright and localhost). TradingIG is native PyQt, so this profile must be reviewed and adapted rather than accepted blindly.
- The existing Python/package/test commands and project risk settings would otherwise remain project customizations.

The official transaction layer refuses to apply a plan while `conflicts` is non-empty. The initial red plan was therefore not applied.

## Conflict-resolved preview awaiting approval

The resolved plan is stored outside the target at `C:\Users\srey\AppData\Local\Temp\TradingIG-SR00-tools\tradingig_sr41_resolved_plan.json` with SHA-256 `2159a54a0c4b8d205637bd04e5168a9abd8d5990963b10c240f8c4c97818d92f`. It uses the official transaction schema, retains current-file guards, and will create an exact restore journal under `docs/codex/upgrade_backups/<transaction-id>/transaction.json` when applied.

- 149 operations, 0 conflicts, 4 project-owned preservations, 0 deletions.
- The same 132 absent pack files listed below will be created.
- `docs/codex/SR_MANAGED_STATE.json` will be created with the resolved fingerprints.
- `AGENTS.md` and `docs/codex/SKILL_MAP.md` retain their current content and receive one official managed block.
- `.gitignore` receives only the official local-authentication ignore entry.
- The following 12 legacy generic method files will be transactionally replaced by the exact official 4.1.0 versions; their former bytes will remain restorable from the transaction journal:
  - `docs/adr/ADR_TEMPLATE.md`
  - `docs/codex/REPO_MAP_POLICY.md`
  - `docs/codex/TOKEN_OPTIMIZATION.md`
  - `docs/codex/WORKFLOW_CODEX.md`
  - `docs/codex/prompts/00_install_codex_environment.md`
  - `scripts/codex/validate_skills.py`
  - `scripts/codex/verify_codex_pack.py`
  - `docs/codex/tasks/_TEMPLATE/decisions.md`
  - `docs/codex/tasks/_TEMPLATE/findings.md`
  - `docs/codex/tasks/_TEMPLATE/progress.md`
  - `docs/codex/tasks/_TEMPLATE/task_plan.md`
  - `docs/codex/tasks/_TEMPLATE/verification.md`
- `docs/codex/PROJECT_PROFILE.yaml` will be transactionally merged rather than replaced:
  - fix the invalid quoting in `gui_import_smoke` without changing its command;
  - set factual project identity to `TradingIG`, key `TIG`, domain `trading`;
  - preserve the current Python, package, test, risk, token and verification configuration;
  - add the missing SR 4.1 policy/harness/knowledge/runtime sections;
  - replace only the method-owned legacy skill catalog and remove the two retired planning/review flags;
  - keep native-Qt visual verification under project control by setting the web Playwright runner `enabled: false` and `required_for_ui_lots: false`.

This exact plan was applied only to `C:\Users\srey\AppData\Local\Temp\TradingIG-SR00-stage2-20261022`. The official post-check returned `ok: true` with no error or warning, and a subsequent official preview returned 0 operations and 0 conflicts.

## Exact 132 proposed creations

- `docs/codex/CHANGELOG.md`
- `docs/codex/NEXUS_CONTEXT_PACK.template.md`
- `docs/codex/SR_INBOX.yaml`
- `docs/codex/SR_LOTS.yaml`
- `docs/codex/SR_PASSES.yaml`
- `docs/codex/AI_AGENT_RUNTIME_METHOD.md`
- `docs/codex/DOMAIN_EXPERTISE_BOOTSTRAP.md`
- `docs/codex/LOT_EXECUTION_METHOD.md`
- `docs/codex/MCP_POLICY.yaml`
- `docs/codex/PROJECT_SKILLS_POLICY.md`
- `docs/codex/SKILL_DIGEST.md`
- `docs/codex/SR_AGENT_METHOD.md`
- `docs/codex/SR_BOOTSTRAP.md`
- `docs/codex/SR_DEVELOPMENT_METHOD.md`
- `docs/codex/SR_HARNESS_METHOD.md`
- `docs/codex/SR_METHOD.md`
- `docs/codex/SR_PACK_VERSION.json`
- `docs/codex/SR_ROUTES.json`
- `docs/codex/UPGRADE_TEST_PLAN.md`
- `docs/codex/procedures/authority.md`
- `docs/codex/procedures/build.md`
- `docs/codex/procedures/completion.md`
- `docs/codex/procedures/context.md`
- `docs/codex/procedures/contracts.md`
- `docs/codex/procedures/design-evidence.md`
- `docs/codex/procedures/evidence.md`
- `docs/codex/procedures/execution.md`
- `docs/codex/procedures/fact.md`
- `docs/codex/procedures/impact.md`
- `docs/codex/procedures/memory.md`
- `docs/codex/procedures/passes.md`
- `docs/codex/procedures/propagation.md`
- `docs/codex/procedures/resume.md`
- `docs/codex/procedures/runtime-goal.md`
- `docs/codex/procedures/skills.md`
- `docs/codex/procedures/ui.md`
- `docs/codex/procedures/verification.md`
- `docs/codex/project-skills/README.md`
- `docs/codex/prompts/01_start_sr_session.md`
- `docs/codex/prompts/05_upgrade_codex_environment.md`
- `docs/codex/prompts/06_verify_sr_installation.md`
- `docs/codex/prompts/07_realign_sr_state_after_upgrade.md`
- `docs/codex/prompts/08_define_sr_passes_from_lots.md`
- `docs/codex/prompts/09_define_sr_lots_from_scope.md`
- `docs/codex/prompts/10_define_domain_skills_from_cis.md`
- `docs/codex/prompts/15_define_runtime_agents.md`
- `docs/codex/prompts/20_generate_domain_skills.md`
- `docs/codex/prompts/30_review_generated_skills.md`
- `docs/codex/prompts/40_transition_existing_project.md`
- `docs/codex/prompts/50_refresh_repomap.md`
- `docs/codex/prompts/60_review_diff_before_close.md`
- `docs/codex/prompts/de/00_install_codex_environment.md`
- `docs/codex/prompts/de/01_start_sr_session.md`
- `docs/codex/prompts/de/05_upgrade_codex_environment.md`
- `docs/codex/prompts/de/06_verify_sr_installation.md`
- `docs/codex/prompts/de/07_realign_sr_state_after_upgrade.md`
- `docs/codex/prompts/de/08_define_sr_passes_from_lots.md`
- `docs/codex/prompts/de/09_define_sr_lots_from_scope.md`
- `docs/codex/prompts/de/15_define_runtime_agents.md`
- `docs/codex/prompts/en/00_install_codex_environment.md`
- `docs/codex/prompts/en/01_start_sr_session.md`
- `docs/codex/prompts/en/05_upgrade_codex_environment.md`
- `docs/codex/prompts/en/06_verify_sr_installation.md`
- `docs/codex/prompts/en/07_realign_sr_state_after_upgrade.md`
- `docs/codex/prompts/en/08_define_sr_passes_from_lots.md`
- `docs/codex/prompts/en/09_define_sr_lots_from_scope.md`
- `docs/codex/prompts/en/15_define_runtime_agents.md`
- `docs/codex/prompts/es/00_install_codex_environment.md`
- `docs/codex/prompts/es/01_start_sr_session.md`
- `docs/codex/prompts/es/05_upgrade_codex_environment.md`
- `docs/codex/prompts/es/06_verify_sr_installation.md`
- `docs/codex/prompts/es/07_realign_sr_state_after_upgrade.md`
- `docs/codex/prompts/es/08_define_sr_passes_from_lots.md`
- `docs/codex/prompts/es/09_define_sr_lots_from_scope.md`
- `docs/codex/prompts/es/15_define_runtime_agents.md`
- `docs/codex/prompts/fr/00_install_codex_environment.md`
- `docs/codex/prompts/fr/01_start_sr_session.md`
- `docs/codex/prompts/fr/05_upgrade_codex_environment.md`
- `docs/codex/prompts/fr/06_verify_sr_installation.md`
- `docs/codex/prompts/fr/07_realign_sr_state_after_upgrade.md`
- `docs/codex/prompts/fr/08_define_sr_passes_from_lots.md`
- `docs/codex/prompts/fr/09_define_sr_lots_from_scope.md`
- `docs/codex/prompts/fr/15_define_runtime_agents.md`
- `docs/codex/prompts/pt/00_install_codex_environment.md`
- `docs/codex/prompts/pt/01_start_sr_session.md`
- `docs/codex/prompts/pt/05_upgrade_codex_environment.md`
- `docs/codex/prompts/pt/06_verify_sr_installation.md`
- `docs/codex/prompts/pt/07_realign_sr_state_after_upgrade.md`
- `docs/codex/prompts/pt/08_define_sr_passes_from_lots.md`
- `docs/codex/prompts/pt/09_define_sr_lots_from_scope.md`
- `docs/codex/prompts/pt/15_define_runtime_agents.md`
- `scripts/codex/audit_codex_pack.py`
- `scripts/codex/audit_sr_project.py`
- `scripts/codex/audit_sr_task_contracts.py`
- `scripts/codex/aurora_token_run.py`
- `scripts/codex/build_pass_runtime_goal.py`
- `scripts/codex/context_budget_report.py`
- `scripts/codex/find_next_session_prompt.py`
- `scripts/codex/generate_repo_map.py`
- `scripts/codex/playwright_auth_smoke.mjs`
- `scripts/codex/render_sr_state.py`
- `scripts/codex/sr_completion_rules.py`
- `scripts/codex/sr_install_transaction.py`
- `scripts/codex/sr_post_install_check.py`
- `scripts/codex/sr_route_check.py`
- `scripts/codex/sr_ui_verify.mjs`
- `scripts/codex/validate_loop_contract.py`
- `scripts/codex/validate_lot_contract.py`
- `scripts/codex/validate_pass_contract.py`
- `scripts/codex/validate_release_docs.py`
- `scripts/codex/validate_scope.py`
- `scripts/codex/validate_sr_contract.py`
- `docs/codex/skills-method/aurora-architecture-check/SKILL.md`
- `docs/codex/skills-method/aurora-architecture-check/agents/openai.yaml`
- `docs/codex/skills-method/aurora-diagnose/SKILL.md`
- `docs/codex/skills-method/aurora-diagnose/agents/openai.yaml`
- `docs/codex/skills-method/aurora-domain-skill-factory/SKILL.md`
- `docs/codex/skills-method/aurora-domain-skill-factory/agents/openai.yaml`
- `docs/codex/skills-method/aurora-lot-runner/SKILL.md`
- `docs/codex/skills-method/aurora-lot-runner/agents/openai.yaml`
- `docs/codex/skills-method/aurora-to-prd/SKILL.md`
- `docs/codex/skills-method/aurora-to-prd/agents/openai.yaml`
- `docs/codex/skills-method/aurora-ui-visual-qa/SKILL.md`
- `docs/codex/skills-method/aurora-ui-visual-qa/agents/openai.yaml`
- `docs/codex/tasks/_TEMPLATE/NEXT_SESSION_PROMPT.md`
- `docs/codex/tasks/_TEMPLATE/context_pack.md`
- `docs/codex/tasks/_TEMPLATE/gate_report.md`
- `docs/codex/tasks/_TEMPLATE/loop_contract.json`
- `docs/codex/tasks/_TEMPLATE/pass_runtime_goal.md`
- `docs/codex/tasks/_TEMPLATE/session_resume.md`
- `docs/codex/tasks/_TEMPLATE/sr_contract.json`
- `docs/codex/tasks/_TEMPLATE/task_state.yaml`

## Stop boundary

SR00 remains incomplete in the real repository until the user explicitly approves the 149-operation resolved plan. R00 and R01 have not started.

