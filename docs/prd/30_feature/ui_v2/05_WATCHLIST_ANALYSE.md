# 05 — Watchlist et analyse détaillée d'un marché

**Référence visuelle « Maquette Watchlist / Analyse » :** consulter [le catalogue des maquettes approuvées](../../95_sources/images/ui_v2/REFERENCE_IMAGES.md). Les PNG originaux ne sont pas encore inclus dans cette branche.

## Mission

Permettre de suivre rapidement 4–5 marchés (par défaut) et d'obtenir une analyse approfondie en changeant de sous-onglet sans perdre le graphique. L'onglet `Graphique` constitue l'espace central de travail; l'IA et le plan de trade sont des panneaux secondaires facultatifs / onglets.

## A. Structure

**Colonne gauche** : watchlist, étoiles/favoris, sous-jacent, dernier cours, variation, état du flux, graphe miniature si coût/performance raisonnable. `+ Ajouter` ouvre recherche catalogue et affectation éventuelle d'un binding; aucune attribution implicite de droit de flux.

**Barre du marché sélectionné** : nom et canonical ID, ticker IG de référence s'il existe, état marché, date de dernière cotation, bid/ask, spread, jour haut/bas, statut OHLC (défaut `WARMING_UP` si insuffisant).

**Centre** : graphique PyQtGraph existant, chandeliers, croix OHLC et zoom, 1/5/15/30 min, H1/H4, un jour si le fournisseur de données l'autorise. EMA, SMA, bandes Bollinger, niveaux support/résistance, entrée, stop, KO, objectif superposables **individuellement**. Pour RSI/MACD/ATR, privilégier des sous-panneaux synchronisés en axe temporel pour ne pas déformer le prix.

**Sous-onglets** : `Graphique`, `Analyse technique`, `Analyse IA`, `Plan de trade`, `Historique`. En mode normal, un petit volet latéral `Résumé rapide` peut exposer 3-5 indicateurs; mode Expert peut détacher l'IA ou le plan de trade en dock. Le chart doit rester plus grand que les panneaux périphériques.

## B. Analyse technique

Table de l'indicateur, valeur, unité, période, seuils et statut; signaux des stratégies TREND_FOLLOW, BREAKOUT, PULLBACK et EVENT_DRIVEN si valide. Chaque indicateur porte source de bougies, timeframe, nombre de bougies clôturées utilisées, âge, continuité, paramètres, raison `WARMING_UP`/`INVALID`. Multi-timeframe explicitement séparé, pas de « RSI H1 » calculé sur M1 en faisant semblant.

Les signaux affichent direction, niveaux, horizon, conditions d'invalidation, source, stratégies concordantes/divergentes, timestamp et expiration. `NO_TRADE` explicité et mis en évidence lorsqu'aucune stratégie ne passe les filtres.

## C. Analyse IA

Résumé en français ou anglais selon UI (contenu externe peut rester dans la langue retournée avec indication), biais directionnel, niveau de risque, confiance source, liste horodatée des preuves et liens vérifiables. Bouton `Analyser à nouveau` avec indication que cela peut coûter des appels OpenAI, progress et budget; aucun appel automatique provoqué par un simple changement d'onglet.

La recherche web IG/OpenAI du produit courant reste consultative. Une analyse peut être disponible en contexte macro mais **non applicable** au produit dérivé faute de binding exact. `STALE` après expiration (10 min dans le parcours actuel), `UNKNOWN` en l'absence d'analyse.

## D. Plan de trade

Afficher **trois résultats distincts** :

- scénario **haussier / LONG** : déclencheur, entrée ou zone, invalidation, objectif, stop structurel/ATR, R/R attendu, éventuel produit dérivé compatible ;
- scénario **baissier / SHORT** : mêmes champs, avec invalidation au-dessus et objectifs en dessous ;
- **NO_TRADE** : conditions bloquantes ou données manquantes.

Le libellé LONG/SHORT exprime la position économique sur le marché sous-jacent. Une option/barrière avec exposition baissière peut s'acheter à l'ouverture, donc l'**ordre IG BUY/SELL** doit être calculé séparément en fonction du contrat documenté et d'une confirmation humaine. Ne pas copier automatiquement une décision SHORT dans un champ `SELL` pour un produit dérivé.

Le bouton `Préparer ticket Paper` ouvre un ticket pré-rempli **en brouillon**, fait repasser les contrôles RiskEngine et exige confirmation explicite. Il ne crée pas d'ordre. Si frais/KO/cotation/FX/lot minimum manquent : `Non évaluable` et suggestions de données à fournir, pas d'ordre.

## E. Détail historique du marché

Journal des signaux et trades sur ce sous-jacent, taux de réussite par stratégie si nombre et qualité des observations suffisants, analyse des faux signaux, coûts, données manquantes. Séparer backtests (simulation) et trades Paper/LIVE réels.

## Exigences

- **GUI2-WATCH-001** : watchlist configurée et identités de marchés stables, un seul marché actif à la fois dans la vue standard.
- **GUI2-WATCH-002** : réutilisation du moteur PyQtGraph et des indicateurs/services existants, sans refaire les calculs dans les widgets.
- **GUI2-WATCH-003** : overlay paramétrable et panneaux indicateurs synchronisés, performances UI préservées.
- **GUI2-WATCH-004** : valeurs/stratégies explicables, complétude OHLC et dates visibles.
- **GUI2-WATCH-005** : vue IA affichant périmètre, sources, fraîcheur, coûts potentiels, statut et limites.
- **GUI2-WATCH-006** : plans LONG, SHORT et NO_TRADE en parallèle, séparés du sens d'ordre du contrat IG.
- **GUI2-WATCH-007** : clic vers brouillon Paper uniquement si données et règles déterministes passent les gates.
- **GUI2-WATCH-008** : le changement de marché ne recycle pas silencieusement l'IA ou les prix de l'instrument précédent.
- **GUI2-WATCH-009** : indication du nombre de bougies nécessaires à la disponibilité des indicateurs, sans forcing d'historique IG.

## Critères d'acceptation

Un M1 incomplet ne devient pas H1 exploitable. Une série session-only après reboot commence à `WARMING_UP`. Une analyse IA d'un CAC 40 LIVE ne s'affiche pas comme applicable à une Barrière DEMO non liée. Un plan SHORT sur barrière PUT ne remplit pas `SELL` sans résolution explicite du produit.
