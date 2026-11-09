# Findings

- `ChartCandleSeries` ne porte pas l'état clôturé/ouvert de chaque bougie.
- La seule politique sûre pour un scan manuel est donc d'exclure la dernière bougie.
- Les composantes contexte, R/R, risque marché et coûts ne sont pas toujours disponibles ; produire
  un score partiel violerait la règle conservative du scanner.
- Le cache M5 observé le 2026-11-05 mélangeait une série REST riche avec un cache stream très
  clairsemé ; restaurer ou fusionner ce cache après redémarrage ne peut pas combler une coupure.
- L'historique fiable doit donc venir d'un snapshot REST court et direct pour le timeframe choisi
  (`60` points) ; le cache local n'est qu'une réutilisation très brève et non une autorité d'analyse.
- Les Barrières/Options d'un même marché réutilisent le sous-jacent de graphique : le cache doit
  être porté par cet EPIC source, pas dupliqué pour chaque Barrière.
- Une série présentant un trou ne peut pas alimenter les indicateurs : seul son suffixe clôturé et
  strictement continu est désormais transmis aux stratégies, qui restent en warmup si insuffisant.
- Un snapshot ancien n'est ni affiché ni utilisé par le Scanner ; le direct seul reste visible tant
  qu'IG ne permet pas de rafraîchir l'historique.
- Un trou au bord du flux déclenche une seule tentative de snapshot REST réparateur, identifiée par
  ses deux timestamps, afin d'éviter une requête répétée à chaque update.
- Les logs prouvent qu'une ancienne requête M5 de `8640` points a réussi le 2026-11-04, puis que
  les appels suivants ont épuisé l'allocation historique hebdomadaire. Une requête actuelle de 60
  points a donc été refusée immédiatement, même sans boucle de retry.
- IG Streaming ne fournit pas l'historique absent. Garantir un démarrage immédiat après une longue
  coupure et un quota IG épuisé exige soit un fournisseur historique secondaire, soit un collecteur
  local permanent ; le cache seul ne peut pas recréer les périodes manquantes.
