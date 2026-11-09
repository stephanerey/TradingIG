# Vérification

- Tests ciblés configuration, Settings, Scanner et GUI après profil indicatif : 98 passés.
- Suite complète hors ligne après profil indicatif et cœur multi-marchés : 457 passés.
- Régressions ticket/risque/DEMO/connexion/streaming/Paper : 68 passées.
- `ruff check src tests`, format ciblé et `git diff --check` : passés.
- Aucun appel externe, ticket, ordre ou activation LIVE/AUTO.
- Le profil indicatif est prérempli une seule fois ; un champ ensuite effacé reste inconnu.
- Un tarif invalide lu sur disque se dégrade en inconnu.
