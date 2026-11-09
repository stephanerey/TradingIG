# 08 — Macro, actualités financières et intelligence artificielle

## Mission

Présenter une vue cohérente des facteurs macroéconomiques / géopolitiques, des événements à venir et des analyses IA tout en assurant la **traçabilité, fraîcheur, portée et droit d'utilisation** des sources.

## Sous-onglets

1. `Actualités & contexte` : titres, source officielle ou provider autorisé, publication/collecte, type, marché concerné, niveau d'importance, résumé, lien et état de vérification.
2. `Calendrier économique` : date/heure locale, zone/pays, publication, consensus/précédent/réalisé **si fournisseur les délivre**, classification de l'impact, marchés concernés et fenêtre de vigilance. Rechercher/filtrer par date/pays/importance.
3. `Contexte global` : régime risk-on/off, taux, USD, VIX (si réellement fourni), or, pétrole, géopolitique, sources, timestamp et bandeau d'état global. Pas de fausses données si seulement les RSS Fed/BCE existent.
4. `Analyses IA` : historique de snapshots, product/underlying scope, modèle, prompt, biais, risque, confidence, sources et expiration, coût et consentement aux appels.

## Qualité et absence d'information

Le projet dispose aujourd'hui de collecte de métadonnées Fed/BCE et d'un adaptateur Trading Economics validé hors ligne sans abonnement connu; leur santé de service ne constitue pas un sentiment directionnel. La recherche web OpenAI est consultative, manuelle, structurée ensuite dans un snapshot d'analyse séparé. Les analyses multi-marchés automatiques coûtent potentiellement des requêtes supplémentaires : **pas d'activation par défaut** dans la nouvelle GUI. Les abonnements, licences, quotas et fréquence sont configurables et contrôlés.

Les badges `green/yellow/red/gray` concernent **l'impact/risque** et pas automatiquement la hausse/baisse du marché; deux indicateurs distincts : `event_risk` (sévérité) et `market_bias` (direction).

## Workflow IA

- `Tester configuration` indique si l'API et son modèle peuvent être utilisés, uniquement via un probe explicitement demandé si cela déclenche coût réseau.
- `Lancer une analyse` : marché/périmètre choisi, synthèse des sources et coût potentiel estimé, confirmation si nécessaire; lancement en worker, annulation UI sûre, statut et résultat.
- `Analyse périodique` : profil de fréquence, budget mensuel/journalier, marchés autorisés, nombre max de recherches, consentement, dates d'expiration; par défaut désactivé pour web/IA multi-marchés.
- `Différences` : macro versus IA, conflit de signaux, désaccord entre stratégie technique et contexte (étiquette prudence, pas arbitrage aveugle du LLM).
- L'intégration scanner/plan de trade reste **consultative**, jusqu'à validation explicite des règles d'entrée déterministes.

## Exigences

- **GUI2-MAC-001** : calendrier et sources avec heure locale/date UTC interne, visibilité de l'impact et filtre.
- **GUI2-MAC-002** : distinction information collectée, analyse IA et fait marché vérifié.
- **GUI2-MAC-003** : contrôles de fraîcheur, expiration, sources et applicable/non applicable par produit.
- **GUI2-MAC-004** : aucun appel IA payant causé par le seul rendu d'un widget.
- **GUI2-MAC-005** : nombre d'appels, coût, budget, statut et autorisation visibles dans paramètres / diagnostics.
- **GUI2-MAC-006** : risque événementiel distinct de sentiment directionnel, dans le dashboard et le scanner.
- **GUI2-MAC-007** : analyse IA lisible en français/anglais selon possibilité, avec traduction des labels UI indépendamment du texte externe.
- **GUI2-MAC-008** : données absentes = inconnu / not applicable sans scores fictifs.

## Acceptation

Sans API de calendrier active, l'onglet affiche l'absence et une procédure de configuration sans inventer CPI/NFP datés. Une recherche web manuelle produit une trace de modèle, source, scope et expiration. Changer d'onglet n'augmente pas le nombre d'appels OpenAI.
