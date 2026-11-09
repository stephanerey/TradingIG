# Plan — portefeuille Paper local et vues de suivi

## Objectif vérifiable

Relier une proposition GUI approuvée à l'exécution strictement locale de `PaperBroker`, puis
projeter l'état de session dans des vues Positions, Ordres et Journal. Aucune commande IG,
persistance implicite, dépendance ou migration n'est autorisée.

## Hypothèses et limites

- Le clic Paper reconstruit et réévalue la proposition avec la cotation courante.
- Le compte reste explicitement `paper/paper/local-paper-preview`.
- Le portefeuille et le journal de ce lot sont en mémoire et perdus à la fermeture.
- Les hypothèses de frais/slippage sont immuables pour une intention donnée.
- Les vues sont informatives : aucune fermeture ou modification de stop n'est exposée ici.

## Approche minimale

1. Ajouter un service de session Paper indépendant de Qt et des adaptateurs IG.
2. Étendre la frontière Paper afin de conserver les hypothèses par intention et de libérer la
   réservation de risque après une clôture automatique confirmée.
3. Ajouter au ticket un bouton d'ouverture Paper séparé, actif uniquement après validation et
   réévaluation au clic.
4. Ajouter des vues read-only Positions/Ordres/Journal et les rafraîchir après soumission ou tick.
5. Vérifier l'idempotence, les vetoes, les clôtures, l'absence d'import/call IG et le viewport
   Windows 960×600.

## Skills déclarées

- `codex-tradingig-paper-execution`
- `codex-tradingig-storage-audit`

## Preuves prévues

- Tests ciblés service Paper, ticket et shell Qt.
- Suite hors ligne complète et régressions protégées des méthodes d'ordre IG.
- `ruff check src tests`, smoke Qt offscreen 960×600, RepoMap et contrôles SR.

