# 01 — Vision UX, navigation et shell permanent

**Statut :** conception validée en intention ; à implémenter par lots.

## 1. Organisation en deux niveaux

**Niveau 1 : navigation principale par sidebar gauche** (icône + texte, repliable en mode compact) :

1. `Dashboard / Tableau de bord`
2. `Marchés / Scanner`
3. `Watchlist / Valeurs suivies`
4. `Positions & Ordres`
5. `Historique / Analytics`
6. `Macro / IA`
7. `Diagnostics`
8. `Paramètres`

**Niveau 2 : onglets propres à chaque page**, persistants lors des allers-retours, mais ne tenant pas la place du header. La page principale utilise un `QStackedWidget` ou équivalent Qt; les pages métiers et le ruban permanent ne doivent pas être recréés à chaque clic. Une éventuelle vue Expert utilisera des docks détachables pour certains panneaux et une sauvegarde de disposition, sans rendre les docks indispensables à la V2.

## 2. Header / bandeau permanent

De gauche à droite, en une ligne principale sur un écran large : identité TradingIG; badge compte `DEMO` ou `LIVE` et type `CFD`/`BARRIER`/`OPTION`; sélection explicite du compte; **solde / equity / fonds disponibles**; PnL **jour / semaine / mois** (valeur et % si données suffisantes); compteur positions ouvertes; IG REST / streaming / fraîcheur de flux; état IA (prête, travail en cours, résultat frais/périmé, erreur); mode d'exécution ANALYSIS/PAPER/etc.; accès aux notifications et arrêt d'urgence selon capacités existantes.

Le header doit rester clair à 1366 × 768 avec DPI 125 %. En largeur insuffisante, les KPI secondaires basculent dans une seconde ligne ou un panneau « Plus », **jamais** le compte, l'environnement, le mode, les alertes critiques ou la fraîcheur des données.

La barre n'est **pas** une preuve que l'IA est « connectée » : un service cloud qui ne reçoit pas d'appel ne possède pas de socket permanent. Afficher `configurée`, `dernière analyse OK il y a…`, `en cours`, `indisponible`, `quota`, `non configurée`, selon des preuves réelles. Les vérifications ne doivent pas envoyer d'appels IA payants sans consentement. Pour IG, distinguer REST authentifié, Lightstreamer abonné et dernière cotation reçue.

## 3. Bandeau de contexte et status bar

Le `MacroRibbonWidget` existant reste visible dans le shell, sous le header, sous une forme compacte (1 ligne) avec éléments cliquables détaillés dans « Macro / IA ». Badge `INCONNU`/gris obligatoire quand la preuve est manquante. `QStatusBar` accueille détails ponctuels et progression sans cacher les erreurs importantes, qui restent dans l'Inbox d'alertes.

## 4. Comportement des pages et sélection croisée

Sélectionner un marché dans Scanner ⇒ ouvrir « Watchlist / Analyse » sur le même **underlying_id** et le timeframe choisi, sans changer silencieusement le compte ni l'EPIC du produit tradé. Choisir une ligne de position ⇒ ouvrir le détail sur « Positions & Ordres », avec l'identité du compte, du produit et de la position; la sélection ne provoque jamais une action broker. Des liens entre Dashboard, Macro, Analyses et Historique conservent le scope et la période. Le changement de compte invalide les projections anciennes et tous les affichages courtiers restent clairement étiquetés.

## 5. Pages et sous-onglets

| Page | Onglets internes suggérés | Vue par défaut |
|---|---|---|
| Dashboard | Vue d'ensemble · Performance · IA / Amélioration | Vue d'ensemble |
| Scanner | Opportunités · Long · Short · À surveiller · Catalogue IG | Opportunités |
| Watchlist | Graphique · Technique · Analyse IA · Plan de trade · Historique du marché | Graphique |
| Positions / Ordres | Positions · En attente · Historique des ordres · Paper · Alertes | Positions |
| Historique | Journal des trades · PnL · Statistiques · Optimisation IA | PnL |
| Macro / IA | Actualités · Calendrier · Contexte global · Analyses IA | Actualités |
| Diagnostics | Santé services · Flux / quotas · Incidents · Journaux | Santé services |
| Paramètres | Comptes · Marchés · Stratégies · Risque · IA · Notifications · Interface · Avancé | Interface ou Comptes |

## Exigences

- **GUI2-NAV-001** : navigation accessible depuis toutes les pages, raccourcis clavier configurables, état actif visuel et libellés traduits.
- **GUI2-NAV-002** : header visible en permanence ; mode et source de données séparés; alerte critique jamais masquée par l'overflow.
- **GUI2-NAV-003** : pages chargées paresseusement si coûteuses, mais une seule instance des services métier et des connexions externes.
- **GUI2-NAV-004** : retour arrière logique / boutons de navigation sans réinitialiser une analyse ou un graphique.
- **GUI2-NAV-005** : sélection du compte et de l'underlying explicites; aucun héritage ambigu d'un produit ou d'un ordre.
- **GUI2-NAV-006** : taille/fenêtre/dernier onglet persistés, restauration versionnée et fallback sain si disposition obsolète.
- **GUI2-NAV-007** : mode fenêtre normal/maximisé ; pas de perte de contrôle avec un DPI différent ou lors du débranchement d'un second écran.
- **GUI2-NAV-008** : fermer la GUI ne doit pas prétendre maintenir le moteur d'ordres logiciels tant que celui-ci reste dans le même processus ; avertissement si des opérations Paper ou pendings sont actifs.
- **GUI2-NAV-009** : sidebar en mode compact (icônes et infobulles) et mode complet ; la fonctionnalité n'exige pas un serveur ou Electron.

## Critères d'acceptation

- À 1920 × 1080 / 1366 × 768 et DPI 100/125/150 %, les badges de compte et d'exécution restent visibles.
- Un changement de page n'entraîne aucune reconnexion, souscription redondante ou requête OpenAI.
- Un switch DEMO/LIVE invalide les vues du compte précédent sans afficher des positions sous le mauvais environnement.
- Restaurer un layout corrompu affiche la disposition par défaut sans planter ni effacer les réglages de trading.
