# Decisions

- Le modèle n'est pas choisi silencieusement : l'utilisateur sélectionne ou saisit un identifiant
  exact avant d'activer le bouton.
- Le test utilise uniquement un signal synthétique et ne branche pas encore OpenAI au scanner réel.
- La clé n'est ni éditable ni persistée par la GUI ; seule sa présence dans le processus est montrée.
- Le test est un appel manuel unique, plafonné à 600 tokens par défaut et 2 000 au maximum.
