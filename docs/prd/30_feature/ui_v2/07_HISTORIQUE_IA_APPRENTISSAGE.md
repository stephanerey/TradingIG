# 07 — Historique, statistiques et IA d'optimisation

## Objectif

Exploiter les transactions passées pour quantifier la performance et construire un **processus d'amélioration contrôlé**. « L'IA apprend des trades » signifie ici : exploiter un dataset historique fiable, repérer des régularités/hypothèses et proposer des changements à **valider et tester**. Cela n'autorise pas un LLM à modifier silencieusement les paramètres ou la politique de risque.

## Pages / sous-onglets

`Journal des trades`, `PnL`, `Statistiques`, `Optimisation IA`.

### Journal des trades

Table filtrable par compte, Paper/Broker, marché, produit, stratégie, direction, période, résultat et qualité de données. Un trade possède un identifiant stable, entrées/sorties, frais, MFE/MAE si disponibles, raison d'entrée et sortie, version des paramètres, version de stratégie, contexte technique/macro/IA et snapshots horodatés. Les propositions refusées et les sorties `NO_TRADE` doivent être interrogeables séparément pour analyser la qualité des opportunités manquées.

### Performance et statistiques

Graphiques de résultats nets périodiques, courbe equity si snapshots réels, drawdown, cumul R, résultats par marché/stratégie/sens/timeframe/heure de la journée, coûts, slippage, expectancy, profit factor, proportion de trades gagnants/perdants/nuls et taille de l'échantillon. Une vue « comparaison de stratégies » nécessite au moins un jeu de données et un intervalle communs.

Aucune statistique de win rate ne doit utiliser des événements en attente ou des ordres refusés comme des pertes économiques. Une série à faible effectif est étiquetée « exploratoire ». Les analyses paper et live sont identifiées et comparées, jamais fusionnées par défaut.

### Optimisation IA — workflow gouverné

1. L'utilisateur sélectionne **scope, période, stratégie, marché, mode et dataset** et vérifie la complétude des données.
2. Un diagnostic déterministe produit statistiques, ventilations et écarts avec la configuration actuelle.
3. Sur action explicite, l'IA examine **des agrégats et faits anonymisés/consentis**, propose des hypothèses : « filtrer les trades proches d'un événement », « réduire exposition durant haute volatilité », « comparer deux trailing stops », etc.
4. Chaque hypothèse devient un `OptimizationProposal` avec **paramètre cible**, ancienne/nouvelle valeur envisagée, hypothèse, preuves, effectif, période, biais possibles, niveau de confiance, risques, coût de recalcul, statut `DRAFT`.
5. Une action `Tester en replay` lance la simulation future-blind avec jeux **train/validation/test chronologiques et versionnés**. Des résultats de backtest non testés hors-échantillon ne sont pas considérés comme acceptés.
6. La page affiche **avant/après**, distribution des résultats (pas seulement gain moyen), drawdown, coûts, sensibilité, test hors échantillon et incertitudes.
7. **Validation humaine explicite** pour proposer une modification de profil de stratégie/risk config; nouvelle version enregistrée et possibilité de rollback. Changement pouvant augmenter le risque journalier/max trade interdit par la simple recommandation IA; nécessite parcours de sécurité dédié.
8. L'adoption et son résultat ultérieur sont suivis, puis la proposition peut être rejetée, retirée ou réévaluée.

Un modèle LLM général ne s'« entraîne » pas automatiquement parce qu'on lui fournit un journal. Le système peut utiliser une boucle d'évaluation et, dans une phase ultérieure, un modèle statistique entraînable si l'historique, les licences et la quantité de données le permettent. Aucun apprentissage continu sur un compte LIVE par ajustement opaque.

## Cautions et confidentialité

- Consentement à l'envoi des données de trading à une IA externe; les IDs de compte, clés, détails personnels sont retirés; les positions/prix/horodatages eux-mêmes peuvent être sensibles — option d'analyse locale déterministe sans envoi externe.
- Conservation de `provider_id`, `model_id`, `prompt_version`, fenêtre temporelle et coût estimé/réel pour les analyses IA.
- Une « amélioration de +X % » ne peut être affichée comme fait que si issue d'une comparaison chiffrée et étiquetée `simulation / hors échantillon / live observé`.
- Alertes anti-overfitting et survivorship bias, look-ahead bias, sélection biaisée et changement de régime; comparer à un baseline et au hasard si pertinent.
- Le moteur de trading reste protégé par les règles déterministes et ne consomme jamais directement du texte libre comme signal d'ordre.

## Exigences

- **GUI2-ANA-001** : journal filtrable, export CSV/JSON expurgé, provenance et distinction Paper/Broker.
- **GUI2-ANA-002** : métriques correctement définies par compte/devise/mode, avec effectif et dates.
- **GUI2-ANA-003** : suivi des paramètres historiques, versions de stratégie et coûts/frais de chaque scénario.
- **GUI2-ANA-004** : `OptimizationProposal` typée, auditable, non exécutable, avec preuves et hypothèses.
- **GUI2-ANA-005** : aucune modification de configuration par simple réception d'une réponse OpenAI.
- **GUI2-ANA-006** : validation hors échantillon et politique de rollback avant activation de modification.
- **GUI2-ANA-007** : consentement explicite avant transmission d'historique de transactions externe.
- **GUI2-ANA-008** : gestion des datasets incomplets ou non versionnés avec état `INSUFFICIENT_EVIDENCE`.
- **GUI2-ANA-009** : séparation des avis IA, résultats réels, résultats Paper et backtests.

## Acceptation

Une suggestion IA « augmenter le risque par trade » n'affecte aucun paramètre sans validation. Un gain hypothétique sans dataset validé est affiché « Hypothèse non testée ». Le projet peut désactiver le provider IA et conserver toutes les statistiques déterministes.
