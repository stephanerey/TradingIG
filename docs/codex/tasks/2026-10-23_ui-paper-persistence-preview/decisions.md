# Décisions validées

- Préférer une migration SQLite v2 additive à un fichier JSON parallèle.
- Checkpoints append-only : aucun `UPDATE` ni `DELETE` applicatif.
- Sauvegarde et restauration uniquement par actions utilisateur explicites.
- Chemin proposé : `~/.trading_ig_assistant/data/trading_ig_assistant.sqlite`.
- Ne stocker ni credentials, ni token, ni clé API, ni identifiant de compte IG.
- Ne jamais restaurer sur une session non vide sans confirmation visible.
- Reporter toute refonte GUI à un lot ultérieur.

Validation humaine reçue le 2026-10-23 avant toute migration ou implémentation.

