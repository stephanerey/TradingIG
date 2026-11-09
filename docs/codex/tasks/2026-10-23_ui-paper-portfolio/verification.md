# Verification

## Résultats

- Baseline ciblée avant mutation : `59 passed`.
- Régressions ciblées finales Paper/ticket/shell/intégration : `68 passed`.
- Suite hors ligne complète : `204 passed in 11.33s`.
- Régressions protégées des méthodes d'ordre IG : `13 passed`.
- `ruff check src tests` : succès.
- `ruff format --check` sur les huit fichiers nouveaux/modifiés du lot : succès.
- Smoke Qt offscreen : fenêtre exacte 960×600, minimum hint 0×137, une position, un ordre,
  deux événements, onglet `Portefeuille Paper` actif.
- Capture locale : `.codex_artifacts/ui-paper-portfolio-960x600.png`.
- RepoMap régénérée ; pack SR 4.1 cohérent ; cinq skills projet valides.
- `git diff --check` : aucun défaut du lot, seulement quatre avertissements LF/CRLF préexistants.
- Branche `chore/sr41-upgrade`, HEAD
  `512c16d59337d2b92bb475daecb96cc902eb00c0` inchangés.

## Limites prouvées

- Le portefeuille et le journal sont en mémoire uniquement et sont perdus à la fermeture.
- Les vues sont read-only : aucune commande manuelle de clôture ou de stop dans ce lot.
- Aucun ordre DEMO/LIVE, appel IG authentifié, dépendance, migration ou base runtime n'a été créé.

