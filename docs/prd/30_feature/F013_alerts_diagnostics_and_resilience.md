# F013 — Alerts, Diagnostics and Resilience

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstructed from the recovered V1.1.

**Last updated:** 2026-10-22

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 15; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-15"></a>

## 15. Alertes, diagnostics et résilience

### 15.1 Notifications

**REQ-ALERT-001/P1** Routeur configurable : Windows toast, e-mail (SMTP ou provider), Telegram bot ; téléphone via notifications du canal choisi, sans imposer une appli mobile native.\
**REQ-ALERT-002/P1** Catégories : opportunité, signal expiré, pending déclenché, ordre confirmé/rejeté/inconnu, stop sécurisé/non confirmé, limite de perte, problème connexion/quota/qualité, reprise et réconciliation.\
**REQ-ALERT-003/P1** Filtrage par sévérité, canal, plage horaire, fréquence, cooldown et acquittement. Les alertes critiques doivent rester consultables dans l'application même si l'envoi externe échoue.\
**REQ-ALERT-004/P1** Les secrets SMTP/Telegram vont au keyring ; masquage dans logs/tests/config/export.

### 15.2 Diagnostic

**REQ-DIAG-001/P0** Vue complète des connexions IG REST/stream, âge dernière quote/bougie, compte courant, état du cache et quota API ; horodatage clair.\
**REQ-DIAG-002/P1** Mesurer erreurs, latences, reconnections, files workers, pending in-flight, occupation DB, gaps, qualité OHLC, fréquence d'updates, et horloge locale/UTC.\
**REQ-DIAG-003/P1** Journal structuré tournant par taille ou jour, niveaux réglables, `correlation_id`, conservation configurable et option export expurgé.\
**REQ-DIAG-004/P0** **Kill switch** logiciel : interdit immédiatement les nouvelles ouvertures; ne désactive pas la surveillance/gestion des positions. Bouton visible, état persistant, audit.\
**REQ-DIAG-005/P0** Mode « dégradation sûre » en cas de flux obsolète, perte réseau, session expirée, quota épuisé ou résultat ordre inconnu : bloquer nouvelles entrées, afficher l'alerte, réconcilier avant reprise.\
**REQ-DIAG-006/P1** Test de notification et test de connectivité disponibles depuis le GUI sans créer d'ordre réel.

### 15.3 Objectifs non fonctionnels et mesurabilité

Les seuils de performance sont des **cibles initiales à mesurer** sur PC Windows de développement, et non des latences garanties par IG :

| Critère | Cible de validation |
|---|---|
| GUI réactive | Un accès REST lent ne bloque jamais la boucle Qt ; commandes GUI utilisables pendant le chargement |
| Refresh GUI | Rafraîchissement limité/coalescé pour éviter un redraw complet à chaque tick |
| Temps signal → passage Risk Engine | Mesuré et journalisé ; seuil d'alerte configurable, pas de promesse de HFT |
| Crash/restart | Récupération des caches/événements puis réconciliation broker avant ouverture |
| Données invalides | Bloquage contrôlé des nouveaux ordres ; diagnostic explicite |
| Tests | `pytest -q`, `ruff check src tests`, smoke GUI Windows, et suites replay/contract selon phase |
| Confidentialité | Secrets uniquement keyring/en mémoire, masqués partout ailleurs |

## V1.2 traceability

[Chapter 4](../10_architecture/overview.md) · [Acceptance matrix](../90_quality/acceptance_matrix.md) · [Definition of Done](../90_quality/definition_of_done.md). Criteria are specifications, not passed test results.

## Goal

Provide configurable alerts, observable diagnostics and safe degradation described in chapter 15.

## Non-goals

No outgoing notification, network connection or kill-switch implementation in this task.

## Constraints

REQ-ALERT and REQ-DIAG govern; external delivery failures must not hide critical local alerts.

## Acceptance criteria

Use AC-016, REQ-DIAG-004/005 and chapter 15.3 measurement criteria.

## Testing notes

Future deterministic delivery-failure, stale-data and reconciliation scenarios; verify safety with fake providers.
