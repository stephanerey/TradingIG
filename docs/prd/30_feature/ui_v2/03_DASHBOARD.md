# 03 — Dashboard / Tableau de bord

**Référence visuelle « Maquette dashboard » :** consulter [le catalogue des maquettes approuvées](../../95_sources/images/ui_v2/REFERENCE_IMAGES.md). Les PNG originaux ne sont pas encore inclus dans cette branche.

## Finalité

Première page à l'ouverture, **synthèse de la performance du compte sélectionné** et de la situation à surveiller. Le dashboard ne doit pas exiger de charger l'intégralité du catalogue IG ou de recalculer tous les signaux.

## A. Vue d'ensemble — disposition proposée

1. Rangée de `KpiCard`: equity/solde, fonds disponibles, PnL J/S/M, positions ouvertes, win rate, profit factor, drawdown (afficher `N/A` si non calculable).
2. Zone « Performance » : **deux graphiques synchronisés sur la même fenêtre et granularité**. À gauche histogramme du PnL **en EUR (ou devise du compte) ou en %**, à droite **courbe du solde/equity du compte**; choix `Jour / Semaine / Mois / Année`, sélecteur de plage de dates et synchronisation curseur et zoom X.
3. Zone « Statistiques ordres / trades » : positions ouvertes, ordres en attente, ordres acceptés/rejetés, trades clôturés gagnants/perdants/nuls, taux de réussite calculé seulement sur trades clôturés avec résultat connu, expectancy et R/R si connu.
4. Zone « IA — bilan et pistes d'amélioration » : tendances observées, risques d'échantillon, propositions *non appliquées*, bouton vers Historique/Optimisation.
5. Zone « Macro / actualités / calendrier » : 3–6 annonces majeures, heure locale, impact, actifs exposés, fraîcheur et source; clic vers Macro/IA.
6. Tableau « Positions ouvertes » : informations essentielles live/Paper à l'écran, tri PnL ou risque, accès détail; taille adaptable, maximum visuel ~8 lignes avec scroll, sans cacher des positions dans les KPIs.

Sous-onglets : `Vue d'ensemble`, `Performance`, `IA / Amélioration`. Les KPI d'en-tête global sont persistants hors dashboard.

## B. Définition financière / source de vérité

- Toute mesure appartient à un **compte**, une devise, un **mode** (`PAPER`, `BROKER`), une période, un instant de calcul et une source. Une vue mixte Paper+Broker nécessite une action volontaire distincte et un marquage explicite; **pas de somme implicite**.
- `PnL net période` : PnL réalisé sur trades clôturés imputés à la période **après frais et financement connus**; afficher un second indicateur latent séparé plutôt qu'y ajouter arbitrairement le PnL ouvert. Les frais manquants rendent le « net certifié » indisponible ou « estimé ».
- `Solde` : balance cash broker vs `Equity` (balance + PnL latent, si définition du fournisseur confirmée). Choix courbe `Equity`/`Solde` explicite; affichage des valeurs historiques uniquement à partir de **snapshots horodatés** ou d'une reconstitution auditable; pas de ligne historique factice obtenue depuis la seule valeur courante.
- `PnL % période` : `PnL net période / equity de début de période * 100` uniquement si ces valeurs sont établies et qu'aucun flux externe (dépôt/retrait) ne fausse la comparaison; sinon `N/A` ou méthode TWR/MWR ultérieure clairement indiquée.
- Aucun passage automatique d'un PnL **réalisé** à un PnL « total » sans changement d'étiquette; les données multidevises exigent taux de conversion daté/traçable ou restent séparées par devise.
- Stats : `ordre accepté/rejeté` = résultat technique d'exécution ; `trade gagnant/perdant` = résultat économique. Un ordre accepté peut finir perdant. `win_rate` exclut les trades ouverts et traite les nuls dans une catégorie explicite.
- La période du graphique barres et de la courbe equity est commune : si une partie de la série manque, afficher un trou et `Données insuffisantes`, jamais compléter par des points inventés.

**Implémentation existante vérifiée** : `services/analytics_service.py::aggregate_realized_pnl()` sait regrouper du PnL réalisé par jour/semaine/mois/année et devise; cela **ne fournit pas** à lui seul la courbe d'equity historique, le taux de réussite ni des performances LIVE vérifiées. Codex doit créer une projection dédiée, sans transformer le module de calcul existant en widget.

## C. Interaction

- Changement granularité J/S/M/A ⇒ actualiser simultanément les deux graphiques, stats et dates.
- Changement devise EUR/% ⇒ conserver les dates/zoom; afficher la formule dans infobulle; si capital de début absent, `N/A` en pourcentage.
- Cliquer une barre ⇒ filtrer la table des trades sur la période; cliquer un point equity ⇒ afficher la date et la provenance du snapshot.
- Choisir une position ⇒ ouvrir détail Positions; clic événement ⇒ ouvrir contexte Macro; clic suggestion IA ⇒ ouvre une proposition en revue, sans appliquer.
- Absence d'historique ⇒ état vide guidant la collecte et la validation, pas de données démo maquillées.

## Exigences

- **GUI2-DASH-001** : tableau de bord par compte et mode, avec période explicitement visible.
- **GUI2-DASH-002** : histogramme PnL EUR/% et ligne solde/equity synchronisés temps/zoom/curseur.
- **GUI2-DASH-003** : calculs financiers tracés aux événements et snapshots; aucune invention de capital passé.
- **GUI2-DASH-004** : séparation ordres techniquement réussis et trades financièrement gagnants.
- **GUI2-DASH-005** : positions ouvertes mises à jour avec prix valide, latence/fraîcheur et contrôles de protection; clic détail.
- **GUI2-DASH-006** : actualités et événements à venir par source / impact et horodatage.
- **GUI2-DASH-007** : suggestions IA d'optimisation consultatives, versionnées, jamais auto-appliquées.
- **GUI2-DASH-008** : recalcul non bloquant et rafraîchissement incrémental; dashboard fonctionnel avec historique incomplet.
- **GUI2-DASH-009** : affichage « aucune donnée / impossible à calculer » pour les statistiques non encore disponibles.

## Critères d'acceptation

Un jeu test avec trois jours (un jour gagnant, un jour perdant, un jour sans trade) rend les barres correctes et les mêmes dates sur la courbe equity; changer en % produit `N/A` si le capital initial est absent. Les ordres rejétés ne sont jamais comptés comme trades perdants. Un compte DEMO et une session Paper ne fusionnent pas leur PnL sans demande explicite.
