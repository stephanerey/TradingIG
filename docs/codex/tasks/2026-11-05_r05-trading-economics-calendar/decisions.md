# Decisions

- Utiliser la bibliothèque standard, sans package Trading Economics.
- Ne jamais placer la clé dans l'URL.
- Mapper les catégories par égalité explicite configurée, jamais par classification libre.
- Conserver `DateSpan=1` avec un tag d'horaire estimé ; le risque peut ainsi rester conservateur.
- Ne retenir une URL source que si elle utilise HTTPS ; elle n'est jamais appelée par l'adaptateur.

