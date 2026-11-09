# Plan — contexte OpenAI périodique de session

## Objectif

Après un probe OpenAI réussi et un consentement périodique explicite, rafraîchir le contexte
consultatif toutes les 15 minutes sans bloquer Qt et sans transmettre de donnée de compte, ticket
ou ordre.

## Périmètre minimal

- Ajouter un consentement périodique non persistant dans Settings > OpenAI.
- Activer un `QTimer` de session seulement après succès du probe.
- Réutiliser le worker et le contrat structuré existants ; ignorer un cycle sans preuve officielle
  ou pendant un appel déjà actif.
- Garder l'IA hors ticket, risque, Paper et broker ; documenter la cible AUTO future séparément.

## Hypothèses et autorité

- Autorité utilisateur explicite reçue le 05/11/2026 pour des appels toutes les 15 minutes après
  validation de session.
- `OPENAI_API_KEY` reste fournie uniquement par l'environnement du processus.
- Aucun appel réel n'est exécuté pendant les tests.

## Skills

- `openai-docs` : contrat Responses/Structured Outputs officiel.
- `codex-tradingig-analysis-scanner` : provenance, UNKNOWN/NO_TRADE et interdiction broker.

## Preuves prévues

- Tests Qt ciblés du consentement, du timer, du non-chevauchement et de la charge transmise.
- Régressions protégées ordre/risque/DEMO/Paper.
- Suite complète, Ruff et `git diff --check`.

