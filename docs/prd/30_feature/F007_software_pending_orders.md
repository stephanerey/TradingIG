# F007 — Software Pending Orders

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Earlier project text is preserved; explicit V1.2 changes take precedence only on documented conflicts. This is not implementation or activation evidence.


> **PRD Policy:** **PROJECT (editable)** — Feature specification.\
**Last updated:** 2026-10-22


## Goal
Implement app-managed delayed entry conditions for Barriers/Options when native IG delayed-order workflow is unavailable, unsuitable, or disabled.

## Non-goals
- MVP does not blindly execute live orders on trigger.
- MVP does not rely on a single tick crossing a level without confirmation.

## Requirements
- Revalidate `MacroRibbonState` at trigger time. A pending order armed during green conditions may be downgraded, paused, or require confirmation if the ribbon turns red/yellow before trigger.
- Pending order states: `DRAFT`, `ARMED`, `TRIGGERED`, `CONFIRMED`, `EXECUTED`, `CANCELLED`, `EXPIRED`, `FAILED`.
- Trigger types:
  - price crosses above/below level;
  - price touches zone;
  - breakout + hold time;
  - candle close above/below level;
  - pullback to zone + rebound confirmation.
- Parameters: instrument/product, direction, trigger level/zone, tolerance, max acceptable slippage, expiry time, confirmation rule, ticket template.
- On trigger, revalidate data freshness, spread, market status, product status, KO distance, R/R, total exposure.
- Alert user and show prepared ticket for manual confirmation.
- Log all state changes.

## Constraints
- Must avoid repeated triggers around the same level via cooldown and state locking.
- Must disable triggers when streaming data is stale.
- Must not open a trade if ticket is invalid at trigger time.

## Acceptance criteria
- A replay test triggers exactly once on a valid breakout.
- A wick without confirmation does not trigger when candle-close confirmation is configured.
- Expired pending orders do not trigger.

## Testing notes
- Replay candle/tick sequences.
- Unit-test state transitions and validation gates.

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 9; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-9"></a>

## 9. Ticket Builder, exécution et ordres conditionnels

### 9.1 Séparation des modes

- `ANALYSIS` : accès lecture/analyse ; **aucun appel de création, mise à jour ni clôture d'ordre** vers le broker, même sur requête IA.
- `SUPERVISED` : signal → proposition → Risk Engine → confirmation humaine visible portant sur **instrument, compte, type de produit, taille, coûts, stop/KO** → commande si API supportée.
- `AUTO` : signal autorisé et non expiré → Risk Engine + capability gate + permissions du compte + limites/kill switch → commande ; journalisation et notifications. Désactivé au démarrage et non disponible avant validation de bout en bout. L'IA n'envoie jamais directement une requête HTTP de trading.
- `PAPER` : environnement d'exécution simulé distinct d'un compte réel, activable depuis n'importe quel mode d'analyse/validation, sans possibilité de fuite d'ordres live.

### 9.2 Commande, idempotence et réconciliation

**REQ-EXEC-001/P0** `OrderIntent` immuable avec identifiant interne unique, compte cible, broker, environnement, produit, paramètres financiers, signal et version de règles.\
**REQ-EXEC-002/P0** Toute commande passe par `RiskEngine` et `OrderExecutionCoordinator` ; aucune UI ni LLM ne peut appeler directement `IGRestAdapter` pour trader.\
**REQ-EXEC-003/P0** Modèle d'états minimal `PROPOSED`, `RISK_CHECKED`, `AWAITING_CONFIRMATION`, `SUBMITTING`, `UNKNOWN`, `BROKER_CONFIRMED`, `OPEN`, `REJECTED`, `CANCELLING`, `CLOSED` ; transitions et erreurs persistées.\
**REQ-EXEC-004/P0** Sur timeout ou réponse ambiguë, état `UNKNOWN`, interrogation de l'état broker et des confirmations avant toute nouvelle soumission ; **ne jamais retenter aveuglément** un ordre susceptible d'avoir été accepté.\
**REQ-EXEC-005/P0** Rapprocher les positions réelles avec l'état local après démarrage, reconnect ou bascule de compte ; ne pas autoriser de nouvelles entrées si la réconciliation critique a échoué.\
**REQ-EXEC-006/P0** Capacité d'ouverture/modification/fermeture Barrières/Options IG soumise à test API représentatif **démo puis compte réel explicitement autorisé**. Si non supportée : mode recommandation/supervisé manuel seulement, jamais contournement.\
**REQ-EXEC-007/P1** Ticket comporte produit/contrat, sens, entrée, taille, stop, take profit, KO/barrière, spread, frais, marge/premium, perte et gain nets estimés, score et commentaire.\
**REQ-EXEC-008/P1** Ordre logiciel différé : états `ARMED`, `TRIGGERED`, `AWAITING_CONFIRMATION`, `EXPIRED`, `CANCELLED`, `SUBMITTED` ; revalidation prix, horaires, compte, signal, risque, quota et état du broker **au déclenchement**, plus cooldown/déduplication.\
**REQ-EXEC-009/P1** Une intention logicielle qui dépend de la GUI active porte une mention explicite « non protégée en cas de coupure/arrêt » ; préférer ordres et stops natifs broker lorsqu'ils existent.\
**REQ-EXEC-010/P1** Paramétrage GUI : mode, confirmations, produits, horaires autorisés, types d'ordres, alertes, prix maximum de déviation, délais d'expiration, limites d'intentions.

## V1.2 traceability

[Chapter 4](../10_architecture/overview.md) · [Acceptance matrix](../90_quality/acceptance_matrix.md) · [Definition of Done](../90_quality/definition_of_done.md). Criteria are specifications, not passed test results.

## Offline AUTO readiness evidence — 2026-10-23

An additive broker-independent gate now models exact account/product/strategy whitelists, immutable
policy and acceptance digests, runtime-generation binding, expiry, session quota, Risk Engine
approval, broker capability, kill switch, reconciliation and ambiguous-execution vetoes. Safe start
is ANALYSIS with the kill switch active and reconciliation incomplete. This gate has no broker
dependency and is not connected to the GUI or an execution coordinator. The current IG adapter's
read-only capability report keeps AUTO ineligible.
