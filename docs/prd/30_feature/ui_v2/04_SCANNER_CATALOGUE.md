# 04 — Marchés / Scanner et catalogue IG

**Référence visuelle « Maquette scanner » :** consulter [le catalogue des maquettes approuvées](../../95_sources/images/ui_v2/REFERENCE_IMAGES.md). Les PNG originaux ne sont pas encore inclus dans cette branche.

## Objectif

Faire du scanner la **porte d'entrée des opportunités**, sans confondre le suivi des *marchés de référence*, l'inventaire des *produits IG* et les *possibilités réelles d'exécution*.

## A. Cinq sous-onglets

`Opportunités` (défaut), `Long / Haussier`, `Short / Baissier`, `À surveiller`, `Catalogue IG`.

Les quatre premiers lisent des projections du **scanner par sous-jacent**. Le catalogue montre **tous les produits découverts et filtrables** à la date du dernier inventaire, même s'ils ne possèdent pas un flux direct exploitable; ne jamais annoncer « temps réel pour tous » si IG limite les abonnements. Seules les références suivies et les produits bénéficiant de droit de flux peuvent être souscrits selon un budget de streaming configuré.

## B. Tableau scanner marchés

Colonnes obligatoires : favori, marché/ID de référence, classe d'actif, dernier cours et devise/unité, variation absolue, variation % et fenêtre, source/âge de cotation, **score technique**, **contexte/score IA**, prochain événement significatif (heure/impact), risque de marché, `LONG / SHORT / NEUTRE / NO_TRADE / INDISPONIBLE`, raison synthétique et dernière évaluation. En expansion facultative : signaux par stratégie, R/R, coûts, qualité OHLC, consensus, bornes de validité, sources.

Les colonnes sont réordonnables, redimensionnables et masquables, avec profils de présentation sauvegardés. Tri stable `score DESC`, `variation`, `heure`, `nom`; les filtres ne détruisent pas l'état du modèle. Le tableau conserve une ligne par marché configuré, même si les données n'ont pas suffi au calcul — statut et raison obligatoires.

## C. Catalogue de produits IG

Colonnes : nom IG, `product_epic`, famille, sous-jacent **confirmé/absent**, environnement/compte associé, direction d'exposition, sens d'ordre disponible, bid/ask/spread, variation, devise, `KO`/strike/échéance si applicable, taille min, statut IG, âge dernière cotation, score technique et sentiment **seulement si hérités d'un binding validé**. Le score de l'underlying doit être intitulé `Contexte du marché de référence`, jamais comme un score du produit dérivé à coût identique. Les données de risque/cout/prime propres au produit ne sont pas héritables.

La recherche ciblée IG actuelle peut ajouter des produits temporairement à la session, distincts du catalogue enregistré : afficher `Découvert en session / non confirmé`. Une correspondance EPIC déduite d'un nom n'est jamais suffisante pour projeter scores et IA. Une Barrière CALL/PUT n'implique pas un ordre BUY/SELL automatiquement.

## D. Scores, fraîcheur et couleurs

Les badges de **composantes** respectent le barème qualitatif métier `100/75/50/0/UNKNOWN`. Le `score global` utilise les pondérations existantes (**30 technique / 15 contexte / 20 R:R / 15 risque marché / 10 coûts / 10 qualité données**) seulement si les entrées indispensables existent et les vetos sont satisfaits. Une analyse IA favorable ne crée pas par compensation un score technique artificiel.

Pour l'affichage du score IA, deux concepts distincts : **contexte directionnel** (`bullish/bearish/neutral/unknown`) et **évaluation de qualité/confiance**, cette dernière calculée ou présentée uniquement si le contrat l'autorise. Les tableaux ne doivent pas transformer librement une confidence LLM en « score de profit ». La confiance IA est une évaluation interne non calibrée de la qualité de sortie, pas une probabilité réelle de réussite.

Variation positive (cours) : texte vert, négative : rouge; mode surbrillance forte en fond coloré optionnel, seuils paramétrables. Un cours en baisse peut être une **opportunité short**, pas un échec. `INCONNU` : gris neutre avec infobulle d'explication.

## E. Mise à jour et limites

- Liste initiale recommandée : US Tech 100, France 40, Allemagne 40, Or Spot, Pétrole US; configuration utilisateur sans plafond fixe produit. D'autres marchés accessibles par recherche/catalogue.
- Service d'analyse multi-marchés existant `ScannerRuntimeBatchService`; le runtime GUI appelle aujourd'hui une mise à jour essentiellement manuelle, donc créer une **politique de scheduling** périodique *avec budget de données* et possibilité pause / rafraîchir. Le scheduler ne crée aucun ordre.
- Rafraîchir les cellules sur changement effectif avec coalescing (p.ex. 250–1000 ms UI), tout en respectant la cadence réelle et les quotas. En absence de nouveau prix, ne pas rafraîchir artificiellement l'heure du prix.
- Les listes peuvent contenir plusieurs centaines de produits : modèle Qt paginé/virtualisé via `QAbstractTableModel`, cache borné, tri/filter `QSortFilterProxyModel`; jamais plusieurs centaines de widgets en lignes recréés à chaque tick.
- Une souscription streaming refusée donne `NO_STREAM_PERMISSION` ou `NOT_SUBSCRIBED`, avec timestamp du dernier snapshot s'il existe. Les données de cotation dérivée ne prouvent pas une OHLC sous-jacente correcte.

## F. Actions

Double-clic marché ⇒ page Watchlist / Analyse sur marché de référence; bouton étoile ⇒ ajouter/retirer favoris; clic événement ⇒ calendrier; clic source ⇒ détail provenance; clic produit ⇒ fiche produit puis ticket Paper *seulement* si ses contraintes sont qualifiées. Aucune ligne n'active un ordre au simple clic.

## Exigences

- **GUI2-SCAN-001** : tableau multi-marchés classé actualisable automatiquement avec pause et statut.
- **GUI2-SCAN-002** : tous les marchés configurés restent visibles avec raison d'indisponibilité plutôt que disparition silencieuse.
- **GUI2-SCAN-003** : scores techniques/IA/contextuels séparés, ordinaux non probabilistes et données manquantes grises.
- **GUI2-SCAN-004** : long/short/à surveiller avec raisonnement explicitement affiché et vetos.
- **GUI2-SCAN-005** : catalogue IG distinct des sous-jacents, recherche/filtres/colonnes, avec respect des droits et quotas.
- **GUI2-SCAN-006** : binding EPIC exact requis pour toute projection de contexte du sous-jacent vers produit.
- **GUI2-SCAN-007** : rendu incrémental scalable, tri/filtre et sélection stables en streaming.
- **GUI2-SCAN-008** : surbrillance forte optionnelle et sans confusion entre sens de marché et succès d'un trade.
- **GUI2-SCAN-009** : horodatages de prix, sentiment et signal distincts et conservés durant les pannes.
- **GUI2-SCAN-010** : états d'erreur liés aux permissions/quotas sans appels REST en boucle.

## Acceptation

Sur 500+ produits de test, le tableau peut être scrollé et filtré sans latence manifeste ni requête IG par cellule. Un binding invalide laisse le score IA `NOT_APPLICABLE`. Une perte de flux rend la ligne stale sans avancer l'horodatage. Un short sur prix en baisse doit afficher direction `SHORT` et variation rouge, **sans** en déduire un PnL négatif.
