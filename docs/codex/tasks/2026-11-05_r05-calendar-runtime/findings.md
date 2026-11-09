# Findings

- Le runtime news remplace actuellement l'état macro complet ; le calendrier doit être composé
  avec les snapshots news conservés, pas injecté isolément.
- Le pattern OpenAI fournit déjà le mécanisme de probe explicite, secret d'environnement et
  `QThread` attendu.
- La qualification des droits de l'abonnement reste une validation humaine distincte.
