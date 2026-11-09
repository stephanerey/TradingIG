# Plan — adaptateur calendrier Trading Economics

## Objectif vérifiable

Implémenter un `EconomicCalendarProvider` Trading Economics strict et injectable, capable de
normaliser un payload JSON borné en `MacroEvent`, sans appel réel, persistance de clé, dépendance,
GUI, ticket ou broker.

## Approche minimale

1. Épingler l'endpoint HTTPS officiel et transmettre la clé uniquement dans `Authorization`.
2. Borner timeout, taille de réponse, nombre d'événements, pays et fenêtre UTC.
3. Valider strictement ID, horaire UTC, précision horaire, importance 1–3, source et doublons.
4. Exiger une table explicite pour les catégories connues ; toute catégorie non mappée devient
   `OTHER` sans inférence textuelle.
5. Injecter transport et horloge pour tests hors ligne ; masquer la clé dans `repr` et payload.

## Autorité et protections

- Intégration Trading Economics autorisée par l'utilisateur le 2026-11-05.
- Aucun appel réel ni ajout de clé sans nouveau besoin de validation/test humain.
- Branche/HEAD : `chore/sr41-upgrade` / `512c16d`, worktree sale préservé.
- AUTO/LIVE, ordres, dépendances et migrations interdits dans ce lot.

## Skill

- `codex-tradingig-analysis-scanner` : provenance, droits, `unknown` conservateur et absence de
  chemin broker.

## Preuve prévue

- Fixtures JSON synthétiques : normalisation, filtrage, mapping, secret, limites et erreurs.
- Tests contexte/événement, protections IG/LIVE/AUTO, suite complète, Ruff/format/diff ciblés.

