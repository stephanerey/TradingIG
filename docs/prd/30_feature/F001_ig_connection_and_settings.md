# F001 — IG Connection and Settings

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Earlier project text is preserved; explicit V1.2 changes take precedence only on documented conflicts. This is not implementation or activation evidence.


> **PRD Policy:** **PROJECT (editable)** — Feature specification.\
**Last updated:** 2026-10-22


## Goal
Provide a secure configuration screen and connection workflow for IG REST and Streaming APIs.

## Non-goals
- No live order execution in P00.
- No plaintext credential files.

## Requirements
- User can configure IG username, password, API key, environment, and preferred account.
- App can authenticate against IG demo first.
- App displays session/account status.
- App can disconnect and clear session state.
- App masks secrets in UI after entry.
- App supports credential persistence via secure keyring and non-persistence mode.

## Constraints
- Secrets must not be logged, exported, or stored in repository files.
- Live mode must be visibly different from demo mode.

## Acceptance criteria
- Settings can be saved and reloaded without exposing password/API key in settings file.
- Demo login retrieves account metadata.
- Failed login displays a clear error and does not leak secrets.

## Testing notes
- Mock keyring and REST adapter.
- Integration test with demo credentials must be opt-in.

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 5; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-5"></a>

## 5. Comptes, sessions et portefeuille

**REQ-ACC-001/P0** Déclarer plusieurs profils (`broker_id`, `environment`, `account_id`, libellé, devise, actif/inactif). Support CFD et Barrières/Options IG.\
**REQ-ACC-002/P0** Afficher simultanément les snapshots des comptes suivis, mais isoler l'identité de chaque commande. L'implémentation peut sérialiser les changements de compte sur une session IG si nécessaire.\
**REQ-ACC-003/P0** Interdire l'exécution d'un ordre si l'API ne confirme pas explicitement le compte cible après changement de contexte. Un compte simplement sélectionné dans la GUI ne constitue pas une preuve.\
**REQ-ACC-004/P0** Consolider P&L, cash/equity, marge et exposition dans une devise de référence configurable. Une conversion FX absente rend le total consolidé `INCOMPLETE` et peut bloquer une nouvelle ouverture.\
**REQ-ACC-005/P0** Une limite globale s'applique à tous les comptes actifs et aux marchés regroupés par sous-jacent économique, non à leurs EPIC distincts.\
**REQ-ACC-006/P1** Historiser snapshots de soldes/positions et écarts entre état local et état broker. Vue compte inclut horodatage et fiabilité.\
**REQ-ACC-007/P1** Permettre d'activer ou exclure chaque compte de l'exécution automatique, indépendamment de sa visibilité.

**Cas d'acceptation ACC :** deux comptes IG affichés ; un changement échoué ne modifie pas le compte effectif ; un ordre vers compte A ne peut être placé sur B ; deux produits du même pétrole comptent comme même marché pour la limite par sous-jacent.

## V1.2 traceability

[Chapter 4](../10_architecture/overview.md) · [Chapter 16](../10_architecture/security_and_auth.md) · [Acceptance matrix](../90_quality/acceptance_matrix.md) · [Definition of Done](../90_quality/definition_of_done.md). Criteria are specifications, not passed test results.
