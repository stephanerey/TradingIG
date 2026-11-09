# Plan — risque événementiel macro structuré

## Objectif vérifiable

Projeter des `MacroEvent` normalisés, explicitement classés `HIGH`, en drapeaux de risque
événementiel traçables dans une fenêtre temporelle fournie par l'appelant, sans fournisseur réseau,
LLM, score directionnel, ticket ou chemin broker.

## Approche minimale

1. Ajouter un service pur qui exige des fenêtres pré/post-événement positives et des timestamps UTC.
2. Ne produire un drapeau rouge que pour `ContextImportance.HIGH`; conserver les autres niveaux
   sans inférence favorable ou défavorable.
3. Réutiliser `normalize_context_flags` puis `MacroContextService` pour les droits, la provenance,
   la fraîcheur et l'agrégat `EventRisk`.
4. Couvrir fenêtres, ordre déterministe, doublons, observation future et droits inconnus.

## Scope et protections

- Autorisé : domaine/service hors ligne, fixtures synthétiques, documentation R05.
- Interdit : nouvelle source externe, dépendance, migration, GUI final, appel OpenAI/IG, ticket,
  Paper, DEMO, LIVE ou AUTO.
- Branche/HEAD protégés : `chore/sr41-upgrade` / `512c16d`; worktree sale préservé.

## Skills

- `codex-tradingig-analysis-scanner` : états unknown, provenance, risque événementiel et absence de
  chemin broker.

## Preuve prévue

- Tests ciblés du nouveau service et des consommateurs de contexte.
- Suite complète, Ruff/format ciblés et contrôle du diff.

