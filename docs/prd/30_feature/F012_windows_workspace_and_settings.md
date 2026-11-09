# F012 — Windows Workspace and Settings

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstructed from the recovered V1.1.

**Last updated:** 2026-10-22

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 12; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-12"></a>

## 12. Interface Windows et configuration intégrale

### 12.1 Structure

**REQ-UI-001/P1** `QMainWindow` avec workspace central à onglets et panneaux détachables/dockables (`QDockWidget` ou architecture Qt équivalente), dispositions sauvegardées/restaurées.\
**REQ-UI-002/P1** Bandeau permanent : mode actuel, état moteur, courtier/comptes, equity/exposition, P&L, drawdown quotidien, santé données et macro-ribbon.\
**REQ-UI-003/P1** Onglets centraux et docks :

| Vue | Contenu minimal |
|---|---|
| `Scanner` | Watchlist, scores par stratégie/consensus, risques, profit espéré, **commentaire**, filtres, détail |
| `Graphiques` | Multi-charts OHLC, timeframes, indicateurs, niveaux entrée/KO/stop/TP, position et historique des signaux |
| `Positions ouvertes` | Compte, marché, sens, taille, entrée, P&L live, KO, stop, TP, mode de sécurisation, état broker |
| `Ordres` | Propositions, ordres pending natifs/logiciels, in-flight, confirmations, annulations, refus |
| `Historique / P&L` | Liste filtrable des trades et statistiques jour/semaine/mois/année, réalisé/latent, frais |
| `Comptes` | CFD, Barrières/Options, equity, capital libre, marge/premium, exposition et devise |
| `Sentiment / Macro` | Événements, liens sources, directional bias, risque IA, confiance, fraîcheur |
| `Diagnostics` | REST, streaming, quota, cache, gaps, threads, erreurs, latence, journal technique |
| `Notifications` | Canaux, catégories, destinataires, historique et test non destructif |
| `Paramètres` | Tous les profils et les réglages validés ci-dessous |

**REQ-UI-004/P1** Paramètres via GUI, y compris modes, risque, comptes activés, plafonds de trades, stratégie, indicateurs, scores et pondérations, alertes, données, cache, thèmes, timezones, historique, AI et trailing.\
**REQ-UI-005/P1** Configuration hiérarchique avec origine visible et priorité `global < broker/compte < marché < stratégie` lorsque pertinent ; éviter les héritages implicites ambigus.\
**REQ-UI-006/P1** Contrôles avec validation de plages/units, aide contextuelle, valeurs restaurables, aperçu d'impact, persistance atomique ; les réglages de sécurité prennent effet sans redémarrage quand possible.\
**REQ-UI-007/P1** Toute action d'ordre présente explicitement compte, environnement (démo/live), symbole, taille, perte estimée et nature réelle/simulée.\
**REQ-UI-008/P1** Fonctionnement continu : erreur visuelle persistante en cas de déconnexion, pas de disparition silencieuse de fenêtre avec positions ouvertes ; option explicite de confirmation à la fermeture et avertissement pour ordres logiciels en attente.\
**REQ-UI-009/P1** Export CSV/JSON sécurisé des transactions, statistiques et diagnostics expurgés.

### 12.2 Valeurs UI par défaut

- Mode `ANALYSIS`, compte réel non autorisé à placer des ordres, scanner actif sur watchlist configurée.
- Graphique M5 ; contexte M15/H1 ; choix M1, M15, H4 configurable.
- R/R minimal pour génération d'une proposition : **2.0** par défaut, modifiable. Ne pas présenter un ratio supérieur comme promesse de gain.
- Pondérations et seuils du scanner selon §7.3.
- Risque par transaction 1 %, seuil journalier 3 %, plafond global 1 et marché 1.
- Break-even net à +1R, trailing désactivé jusqu'à paramétrage explicite.
- Notifications Windows activables ; e-mail/Telegram désactivés jusqu'à configuration des destinataires et tests.

## V1.2 traceability

[Chapter 4](../10_architecture/overview.md) · [Acceptance matrix](../90_quality/acceptance_matrix.md) · [Definition of Done](../90_quality/definition_of_done.md). Criteria are specifications, not passed test results.

## Goal

Provide the Windows dock/tab workspace and validated settings described in chapter 12.

## Non-goals

No platform migration, new UI implementation or live enabling in this documentation task.

## Constraints

REQ-UI-001–009 and D-011 govern. Resolve the settings-precedence conflict before implementation.

## Acceptance criteria

Verify persisted layouts, settings validation, visible identity/mode and non-blocking loading against chapter 12.

## Testing notes

Future native Windows/Qt tests and sanitized visual inspection; no browser-only substitute for native GUI.

## Partial implementation evidence — 2026-10-23

The product panel exposes compact `Marché` and scrollable `Ticket Paper` tabs. The provisional ticket UI offers relative stop/target distances (`4/12` by default) and an explicit absolute-price mode; both produce visible absolute levels before evaluation, while Barrier KO remains absolute. The standard 1,000 EUR/1 %/size 1 profile also starts with a 9 EUR Paper-only KO-loss assumption and a visible review warning. It requires a recently received direct quote, minimum R/R and explicit Barrier KO-loss estimate. When IG product metadata omits currency, the UI requires a three-letter human confirmation; it never infers currency, and a non-EUR product still requires an explicit FX rate. An explicit action can open a strictly local, risk-revalidated Paper position and project it into Positions, Orders and Journal tabs. The selected open position exposes local-only stop-tightening and manual-close actions; Orders and Journal remain audit projections. Two explicit controls save the local session or restore the latest checksummed checkpoint; no database is opened at startup, and replacement of a non-empty session requires confirmation. The session cannot call IG. A complete GUI redesign is intentionally deferred until functional development stabilizes; the complete dock/tab workspace and the remaining REQ-UI-001–009 views are not claimed complete.
