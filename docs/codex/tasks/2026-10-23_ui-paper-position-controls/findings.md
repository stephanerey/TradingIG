# Constats

- `PaperBroker` possède déjà `move_stop` et `close`, isolés des adaptateurs IG.
- `PaperSessionService` ne les expose pas encore à la GUI.
- `PaperPortfolioWidget` est une projection sans actions.
- Les confirmations broker sont journalisées ; les refus d'action doivent être ajoutés au
  journal de session pour conserver la raison.
- La vue 960×600 conserve les actions visibles ; la première position ouverte est sélectionnée
  automatiquement.
- L'utilisateur a confirmé manuellement que l'ouverture apparaît uniquement dans le portefeuille
  Paper local et non chez IG, conformément à la frontière attendue.

