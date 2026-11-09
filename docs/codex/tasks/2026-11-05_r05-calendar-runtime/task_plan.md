# Plan — runtime calendrier Trading Economics

## Objectif vérifiable

Exposer une validation manuelle Trading Economics dans Settings puis, après succès dans la même
session, rafraîchir le calendrier hors de la boucle Qt et projeter les événements HIGH dans le
risque événementiel déterministe.

## Étapes

1. Ajouter une collecte dégradable et un résultat de refresh typé.
2. Ajouter un onglet Settings : clé d'environnement masquée, pays et fenêtres explicites,
   consentement à un appel potentiellement facturé.
3. Exécuter probe et refresh dans un `QThread`.
4. Composer news + calendrier sans perdre les signaux existants.
5. Couvrir absence de clé, échec, non-blocage Qt, résultat conservateur et protections d'ordre.

## Limites

- Aucun appel réel pendant l'implémentation et les tests.
- Droits Trading Economics `UNKNOWN` : les événements restent gris tant que l'abonnement n'est pas
  qualifié.
- Aucun score directionnel, ticket, ordre, AUTO ou LIVE.
- Aucun secret persisté ni affiché.
