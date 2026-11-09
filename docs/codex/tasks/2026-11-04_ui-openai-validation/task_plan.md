# Plan — validation OpenAI visible dans la GUI

## Objectif vérifiable

Remplacer l'onglet Application vide par un panneau OpenAI permettant de constater la présence de
`OPENAI_API_KEY`, de choisir explicitement un modèle et de lancer un unique test synthétique borné
sans bloquer Qt.

## Périmètre et hypothèses

- Projet autorisé : `C:\Projects\TradingIG`, branche et modifications locales préservées.
- Aucun appel automatique, donnée IG, ordre, stockage de clé ou activation de stratégie.
- La clé reste fournie par l'environnement du processus et n'est jamais affichée.
- Le clic de l'utilisateur, après acknowledgement explicite, autorise uniquement le test affiché.

## Approche minimale

1. Extraire le probe synthétique existant dans un service partagé par le CLI et la GUI.
2. Ajouter un onglet OpenAI aux Settings et un worker `QThread` dédié.
3. Ajouter les régressions GUI/service et exécuter les contrôles ciblés puis globaux.

## Skills

- `openai-docs` : authentification et endpoint OpenAI officiels.
- `codex-tradingig-analysis-scanner` : conserver le contexte IA sans conseil ni exécution.
- `aurora-ui-visual-qa` : inspection du panneau Qt rendu à sa taille réelle.

## Preuve prévue

- Tests unitaires du panneau, du worker non bloquant et du service synthétique.
- `ruff check`, tests complets, smoke GUI hors connexion.
- Validation humaine finale dans Settings > OpenAI uniquement.
