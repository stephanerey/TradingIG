# TradingIG V1.2 — Project Conventions

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstructed from the recovered V1.1.

**Last updated:** 2026-10-22

## Goal

Consolidate V1.1 requirements into the existing modular PRD while preserving local customizations. V1.2 means the local reconstruction authorized on 2026-10-22, not a byte-identical recovery of the unavailable conversation pack.

## Non-goals

No SR installation, application implementation, dependency installation, branch creation, broker connection or trading activation.

## Constraints and precedence

- Locked templates stay byte-identical. This project extension permits French imported requirements alongside existing English documents; filenames and IDs remain stable.
- Keep F001–F011, API001–API003 and Pxx history. Add F012/F013 for workspace/settings and alerts/diagnostics. SR00/R00–R08 are future execution phases, not completed work.
- The modular PRD is the operational source of truth. Archived source inputs are non-normative. The chapter mapping resolves original § references.
- D-005–D-012 explicitly reconcile changes. Compatible original customizations remain applicable; any other substantive conflict stays open for resolution.
- Code and actual checks establish implementation facts. Source audits remain historical. Local baseline: 512c16d59337d2b92bb475daecb96cc902eb00c0, branch chore/sr41-upgrade.
- SR version/date/installer claims are inherited, not newly verified. Verify the official source and commit during SR00; the existing AGENTS.md still governs until an approved method upgrade.
- Keep the current branch. Branch names in source prompts are historical examples, not permission to create or switch branches automatically.
- Source default display timezone Europe/Paris remains configurable and is distinct from the user's Europe/Berlin workstation context. No setting is changed.

## Acceptance criteria

Map all 24 chapters and explicit REQ/AC definitions; preserve all original files and locked templates; resolve local links; restrict the patch to documentation.

## Testing notes

Verify coverage, identifiers, relative paths/anchors, original-file hashes and Git diff. Runtime proofs belong to separately authorized phases.

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 0; [chapter mapping](v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-0"></a>

## 0. Mode d'emploi du PRD

- **MUST / Obligatoire :** exigence nécessaire pour accepter la phase concernée.
- **SHOULD / Recommandé :** comportement attendu sauf arbitrage documenté.
- **MAY / Optionnel :** extension permise mais non imposée.
- **P0 :** fondation et sécurité, avant toute exécution réelle. **P1 :** V1 fonctionnelle supervisée. **P2 :** extension progressive / IA quantitative / automatique.
- Les identifiants `REQ-*`, `AC-*`, `ADR-*` sont stables et doivent être repris dans les commits, les tests et le tableau de tâches.
- **Un paramètre fonctionnel mentionné dans ce document doit être modifiable depuis la GUI**, sauf s'il s'agit d'une constante technique intrinsèque ou d'une garde de sécurité non contournable. Il doit être validé, persisté et décrit.
