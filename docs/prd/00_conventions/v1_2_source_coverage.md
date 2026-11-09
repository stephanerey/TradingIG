# V1.2 Source Coverage and Provenance

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstructed from the recovered V1.1.

**Last updated:** 2026-10-22

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 21; [chapter mapping](v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-21"></a>

## 21. Correspondance avec la documentation existante

| Document du dépôt | Action Codex |
|---|---|
| `docs/prd/PRD.md`, `01_product/*` | Réviser vision, mode auto à terme, décisions, KPIs, scope et risques |
| `10_architecture/overview.md`, `module_boundaries.md`, `main_flows.md` | Ajouter interfaces broker/data, runtime GUI permanent, multi-comptes et exécution sûre |
| `10_architecture/data_schema.md` | Réviser snapshots, instruments, fills, événements, signaux non exécutés, IA, FX et config |
| `F001`, `F002`, `API001`, `API002` | Étendre les comptes, capabilities, quotas et processus de validation IG |
| `F003` | Qualité OHLC, cache, threading, timeframes, warmup |
| `F004` | Stratégies, scoring pondéré et **colonne commentaire** |
| `F005`, `F011`, `API003` | Sentiment, confiance, fournisseurs, provenance et macro ribbon |
| `F006` | Risk Engine 1 %/3 %, exposures, KO, ticket net et limites de positions |
| `F007`, `F008` | Pending, réconciliation, mode auto, break-even net, sécurisation, trailing |
| `F009`, `F010` | Recorder des non-trades, P&L agrégé, imports et replay réaliste |
| `02_tasks/*` et `05_coding_agent/*` | Ajouter SR00 puis phases R00–R08 ; remplacer les anciennes consignes procédurales par les routes SR 4.1 sans effacer les traces historiques |
| `AGENTS.md`, `docs/codex/SR_*`, `PROJECT_PROFILE.yaml` | Réconcilier via l’installateur **officiel**, avec rapport preview/upgrade et validation de préservation ; ne pas éditer manuellement le noyau géré avant le diagnostic |
| `90_quality/*`, `AGENTS.md`, `CURRENT_STATE.md` | Mettre à jour gates sécurité, définition de Done et suivi d'exécution |

## Canonical chapter map

All 24 chapters are transferred without rewriting their requirement text. Each chapter has one canonical location; source copies under 95_sources are non-normative. D-005–D-012 and the conventions extension explain current scope, phase, language and execution boundaries. The §21 action table above describes source intent; it does not authorize editing AGENTS.md or installing SR during consolidation.

| Source chapter | Canonical module |
|---|---|
| 0 — Mode d'emploi du PRD | [00_conventions/tradingig_v1_2_conventions.md](tradingig_v1_2_conventions.md) · [chapter anchor](tradingig_v1_2_conventions.md#source-section-0) |
| 1 — Vision, objectif et frontières | [01_product/product_brief.md](../01_product/product_brief.md) · [chapter anchor](../01_product/product_brief.md#source-section-1) |
| 2 — Décisions fermes et valeurs par défaut | [01_product/decisions.md](../01_product/decisions.md) · [chapter anchor](../01_product/decisions.md#source-section-2) |
| 3 — Baseline vérifiée du dépôt et stratégie de reprise | [20_refactor/codebase_findings.md](../20_refactor/codebase_findings.md) · [chapter anchor](../20_refactor/codebase_findings.md#source-section-3) |
| 4 — Architecture cible | [10_architecture/overview.md](../10_architecture/overview.md) · [chapter anchor](../10_architecture/overview.md#source-section-4) |
| 5 — Comptes, sessions et portefeuille | [30_feature/F001_ig_connection_and_settings.md](../30_feature/F001_ig_connection_and_settings.md) · [chapter anchor](../30_feature/F001_ig_connection_and_settings.md#source-section-5) |
| 6 — Données de marché et OHLC | [30_feature/F003_realtime_market_data_and_charts.md](../30_feature/F003_realtime_market_data_and_charts.md) · [chapter anchor](../30_feature/F003_realtime_market_data_and_charts.md#source-section-6) |
| 7 — Analyse technique, stratégies et scanner | [30_feature/F004_market_scanner_and_setup_scoring.md](../30_feature/F004_market_scanner_and_setup_scoring.md) · [chapter anchor](../30_feature/F004_market_scanner_and_setup_scoring.md#source-section-7) |
| 8 — Moteur de risque et dimensionnement | [30_feature/F006_ticket_builder_and_risk_engine.md](../30_feature/F006_ticket_builder_and_risk_engine.md) · [chapter anchor](../30_feature/F006_ticket_builder_and_risk_engine.md#source-section-8) |
| 9 — Ticket Builder, exécution et ordres conditionnels | [30_feature/F007_software_pending_orders.md](../30_feature/F007_software_pending_orders.md) · [chapter anchor](../30_feature/F007_software_pending_orders.md#source-section-9) |
| 10 — Trade Manager et sécurisation | [30_feature/F008_trade_monitor_and_dynamic_stop_manager.md](../30_feature/F008_trade_monitor_and_dynamic_stop_manager.md) · [chapter anchor](../30_feature/F008_trade_monitor_and_dynamic_stop_manager.md#source-section-10) |
| 11 — Analyse macro, sentiment et IA | [30_feature/F005_macro_news_context_engine.md](../30_feature/F005_macro_news_context_engine.md) · [chapter anchor](../30_feature/F005_macro_news_context_engine.md#source-section-11) |
| 12 — Interface Windows et configuration intégrale | [30_feature/F012_windows_workspace_and_settings.md](../30_feature/F012_windows_workspace_and_settings.md) · [chapter anchor](../30_feature/F012_windows_workspace_and_settings.md#source-section-12) |
| 13 — Historique, recorder et statistiques | [30_feature/F009_trade_journal_and_analytics.md](../30_feature/F009_trade_journal_and_analytics.md) · [chapter anchor](../30_feature/F009_trade_journal_and_analytics.md#source-section-13) |
| 14 — Backtesting, paper trading et validation quantitative | [30_feature/F010_backtesting_and_replay.md](../30_feature/F010_backtesting_and_replay.md) · [chapter anchor](../30_feature/F010_backtesting_and_replay.md#source-section-14) |
| 15 — Alertes, diagnostics et résilience | [30_feature/F013_alerts_diagnostics_and_resilience.md](../30_feature/F013_alerts_diagnostics_and_resilience.md) · [chapter anchor](../30_feature/F013_alerts_diagnostics_and_resilience.md#source-section-15) |
| 16 — Sécurité, déploiement et exploitation | [10_architecture/security_and_auth.md](../10_architecture/security_and_auth.md) · [chapter anchor](../10_architecture/security_and_auth.md#source-section-16) |
| 17 — Contrats d'API/domaines à fournir à Codex | [10_architecture/domain_contracts.md](../10_architecture/domain_contracts.md) · [chapter anchor](../10_architecture/domain_contracts.md#source-section-17) |
| 18 — Plan d’implémentation obligatoire pour Codex | [05_coding_agent/sr41_development_workflow.md](../05_coding_agent/sr41_development_workflow.md) · [chapter anchor](../05_coding_agent/sr41_development_workflow.md#source-section-18) |
| 19 — Grille de tests d'acceptation de bout en bout | [90_quality/acceptance_matrix.md](../90_quality/acceptance_matrix.md) · [chapter anchor](../90_quality/acceptance_matrix.md#source-section-19) |
| 20 — Risques ouverts, limites externes et jalons bloquants | [01_product/risks_and_assumptions.md](../01_product/risks_and_assumptions.md) · [chapter anchor](../01_product/risks_and_assumptions.md#source-section-20) |
| 21 — Correspondance avec la documentation existante | [00_conventions/v1_2_source_coverage.md](v1_2_source_coverage.md) · [chapter anchor](v1_2_source_coverage.md#source-section-21) |
| 22 — Definition of Done générale | [90_quality/definition_of_done.md](../90_quality/definition_of_done.md) · [chapter anchor](../90_quality/definition_of_done.md#source-section-22) |
| 23 — Premier prompt de démarrage Codex | [05_coding_agent/sr00_start_prompt.md](../05_coding_agent/sr00_start_prompt.md) · [chapter anchor](../05_coding_agent/sr00_start_prompt.md#source-section-23) |

## Provenance and preservation

Archive SHA-256: E5D724BE71398269AA92E0FE48857758D03868786A25EF6CD40E1339D3E00F6B. Baseline commit: 512c16d59337d2b92bb475daecb96cc902eb00c0. All 100 pre-existing PRD files must remain; 41 locked Markdown templates and six images must remain byte-identical. New modules extend the existing hierarchy. No branch, runtime, dependency or SR installation change belongs to this delivery.

Transcription formatting: trailing-space hard breaks use Markdown backslashes and terminal newlines are normalized. Chapter coverage is verified after that formatting normalization; requirement wording and IDs are unchanged.
