# Concrete consolidation preview

Date: 2026-10-22. Prepared before applying the PRD changes. Authorization: the user approved reconstructing the missing V1.2 from the recovered V1.1 and consolidating it locally.

## Baseline and source

- Repository: C:\Projects\TradingIG; branch chore/sr41-upgrade; HEAD 512c16d59337d2b92bb475daecb96cc902eb00c0; initially clean.
- Source archive SHA-256: E5D724BE71398269AA92E0FE48857758D03868786A25EF6CD40E1339D3E00F6B.
- 100 pre-existing PRD files; preserve all, including 41 locked templates and six images byte-for-byte.
- 24 source chapters and 125 explicitly defined REQ identifiers transferred to canonical modules without rewriting their source text. Five original Markdown inputs archived separately as non-normative provenance.

## Exact proposed scope

38 existing documentary files modified and 23 new documentary files created below. In addition, this task folder contains planning, preview, baseline and verification evidence. No deletion, application/configuration change, branch change or installation.

### Existing files to modify

- `docs/CURRENT_STATE.md`
- `docs/prd/01_product/decisions.md`
- `docs/prd/01_product/kpis.md`
- `docs/prd/01_product/product_brief.md`
- `docs/prd/01_product/risks_and_assumptions.md`
- `docs/prd/01_product/roadmap.md`
- `docs/prd/02_tasks/tasks_now.md`
- `docs/prd/10_architecture/data_and_paths.md`
- `docs/prd/10_architecture/data_schema.md`
- `docs/prd/10_architecture/environments_and_deployment.md`
- `docs/prd/10_architecture/logging_and_errors.md`
- `docs/prd/10_architecture/main_flows.md`
- `docs/prd/10_architecture/module_boundaries.md`
- `docs/prd/10_architecture/overview.md`
- `docs/prd/10_architecture/package_layout.md`
- `docs/prd/10_architecture/runtime_environment.md`
- `docs/prd/10_architecture/security_and_auth.md`
- `docs/prd/20_refactor/codebase_findings.md`
- `docs/prd/30_feature/API001_ig_rest_adapter.md`
- `docs/prd/30_feature/API002_ig_streaming_adapter.md`
- `docs/prd/30_feature/API003_news_and_macro_adapters.md`
- `docs/prd/30_feature/F001_ig_connection_and_settings.md`
- `docs/prd/30_feature/F002_product_discovery_and_selection.md`
- `docs/prd/30_feature/F003_realtime_market_data_and_charts.md`
- `docs/prd/30_feature/F004_market_scanner_and_setup_scoring.md`
- `docs/prd/30_feature/F005_macro_news_context_engine.md`
- `docs/prd/30_feature/F006_ticket_builder_and_risk_engine.md`
- `docs/prd/30_feature/F007_software_pending_orders.md`
- `docs/prd/30_feature/F008_trade_monitor_and_dynamic_stop_manager.md`
- `docs/prd/30_feature/F009_trade_journal_and_analytics.md`
- `docs/prd/30_feature/F010_backtesting_and_replay.md`
- `docs/prd/30_feature/F011_global_market_context_ribbon.md`
- `docs/prd/30_feature/feature_index.md`
- `docs/prd/90_quality/definition_of_done.md`
- `docs/prd/90_quality/non_functional_requirements.md`
- `docs/prd/90_quality/testing.md`
- `docs/prd/95_sources/index.md`
- `docs/prd/PRD.md`

### New files to create

- `docs/prd/00_conventions/tradingig_v1_2_conventions.md`
- `docs/prd/00_conventions/v1_2_source_coverage.md`
- `docs/prd/02_tasks/phases/R00_baseline.md`
- `docs/prd/02_tasks/phases/R01_ohlc_reliability.md`
- `docs/prd/02_tasks/phases/R02_adapter_contracts.md`
- `docs/prd/02_tasks/phases/R03_accounts_and_risk.md`
- `docs/prd/02_tasks/phases/R04_storage_and_workspace.md`
- `docs/prd/02_tasks/phases/R05_analysis_and_scanner.md`
- `docs/prd/02_tasks/phases/R06_paper_and_trade_manager.md`
- `docs/prd/02_tasks/phases/R07_ig_demo_and_supervised_gate.md`
- `docs/prd/02_tasks/phases/R08_optional_automation.md`
- `docs/prd/02_tasks/phases/SR00_method_upgrade.md`
- `docs/prd/05_coding_agent/sr00_start_prompt.md`
- `docs/prd/05_coding_agent/sr41_development_workflow.md`
- `docs/prd/10_architecture/domain_contracts.md`
- `docs/prd/30_feature/F012_windows_workspace_and_settings.md`
- `docs/prd/30_feature/F013_alerts_diagnostics_and_resilience.md`
- `docs/prd/90_quality/acceptance_matrix.md`
- `docs/prd/95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md`
- `docs/prd/95_sources/md/PROMPT_CODEX_TradingIG_Reprise_R00_R01_SR4.1.md`
- `docs/prd/95_sources/md/PROMPT_CODEX_TradingIG_SR00_Upgrade_SR4.1.md`
- `docs/prd/95_sources/md/TradingIG_Addendum_SR_Method_4.1.md`
- `docs/prd/95_sources/md/TradingIG_Audit_Reprise_2026-10-20.md`

## Conflict treatment

| Conflict | Treatment |
|---|---|
| V1.2 source unavailable | Explicit reconstruction label and original V1.1 provenance; no claim to recover the inaccessible pack |
| Existing customizations and LOCKED templates | Preserve original content; add scoped canonical chapters and traceability; no locked edits |
| French source versus English template | Project-specific extension; original locked conventions unchanged |
| Existing application versus bootstrap task board | Retain historical tasks; record actual observed baseline; add separate restart board without false DONE claims |
| Pxx versus SR00/Rxx; older audit R07 versus final PRD R07/R08 | Preserve history; source PRD chapter 18 controls target roadmap |
| Manual MVP versus future automatic execution | Document staged optional progression; no real-trading activation |
| Generic overrides, old states, REST-first loading | Explicit D-009/D-010 precedence for deterministic safety, confirmed states and cache-first access |
| Preliminary UI/runtime/schema/API choices | State target versus observed implementation; defer migrations and capability evidence |
| SR 4.1 target versus old installed method | Preserve current AGENTS/method; do not install or claim compliance |
| Risk/UI inheritance disagreement | Keep as explicit unresolved design conflict; block dependent settings design, not this documentary consolidation |
| BUG-DATA-003 versus BUG-UI-003 | Record source naming erratum; no code change |

## Pre-application checks

All 24 chapter transfers and all 125 source REQ definitions are present; no locked target is selected. 386 local Markdown links/anchors checked in the candidate document set; the only two initial inventory misses pointed to task_plan.md and verification.md, which already exist in this task folder and were outside that candidate-only inventory. Final filesystem checks will include these files.

## Decision

Proceed under the user's existing reconstruction/consolidation authorization. Preserve the unresolved design question visibly; do not invent a precedence or begin dependent implementation. Final verification and actual file counts will be recorded in verification.md.

