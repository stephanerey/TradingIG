# Décisions

- Identifiants stables : `ig`, `tavily`, `gdelt`, `fred`, `eia`, `openai`.
- Entrées keyring : service `trading-ig-assistant-api-providers`, clé logique
  `provider:<provider_id>:api-key`.
- Les clés sauvegardées dans keyring priment sur l'environnement.
- La suppression d'une clé keyring révèle explicitement le repli environnement restant.
- Le bouton Afficher ne révèle la clé que huit secondes avant de vider le champ.
- Les tests de connexion ne démarrent qu'après un clic explicite et s'exécutent hors du thread GUI.
