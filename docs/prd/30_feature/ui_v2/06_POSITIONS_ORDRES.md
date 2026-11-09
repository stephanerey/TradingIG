# 06 — Positions, ordres, Paper et contrôles de risque

**Référence visuelle « Maquette Positions et ordres » :** consulter [le catalogue des maquettes approuvées](../../95_sources/images/ui_v2/REFERENCE_IMAGES.md). Les PNG originaux ne sont pas encore inclus dans cette branche.

## Objectif

Un tableau central lisible **en temps réel quand le flux le permet** pour surveiller toute exposition ouverte, avec les niveaux de protection et les actions disponibles. Le tableau reste **informateur** quand l'ordre broker est bloqué ; l'apparence d'un bouton ne doit jamais autoriser une fonction non qualifiée.

## A. Sous-onglets

`Positions ouvertes` (défaut), `Ordres en attente`, `Historique des ordres`, `Trading Paper`, `Alertes`.

### Positions ouvertes

Colonnes obligatoires : environnement et compte, `position_id` IG ou Paper, marché/produit/EPIC, type (CFD/Barrière/Option), exposition LONG/SHORT, **sens d'ordre d'ouverture** BUY/SELL, quantité et unité, prix d'entrée, dernier prix de valorisation et âge, PnL net/estimé devise et %, stop loss actif et source broker/logiciel, KO si applicable, limite/TP, risque courant, état (`OPEN`, `PROTECTED`, `TRAILING`, `CLOSING`, `UNCERTAIN`, `CLOSED`), ouverture, statut de synchronisation broker. Les colonnes secondaires peuvent être masquées, mais les niveaux et l'identité ne doivent pas disparaître dans une infobulle.

Le résumé en haut inclut nombre de positions, exposition brute, PnL latent (estimé ou réel et devise), perte restante théorique sous stop/KO **avec caveat slippage/gap**, nombre de protections non confirmées. Tout prix absent marque le PnL comme stale/indisponible.

### Ordres en attente

Séparer `NATIF_IG` et `LOGICIEL_LOCAL` ; déclencheur, conditions, expiration, dernière validation, état, source de prix, confirmation humaine requise, contraintes de réévaluation. Un pending local cesse d'être fiable si le programme ne tourne plus ou si le flux est stale ; l'interface l'annonce sans ambiguïté.

### Trading Paper

Réutiliser **PaperTicketWidget**, **PaperPortfolioWidget**, **PaperSessionService** et les safeguards existants. Les actions locales `ouvrir`, `resserrer stop`, `fermer`, `sauvegarder`, `restaurer` restent explicites. Ne pas changer la politique actuelle de restauration : **aucune base Paper automatiquement ouverte au démarrage**, récupération seulement sur action utilisateur tant que cette décision n'a pas été révisée.

### Historique et alertes

Afficher confirmation/rejet broker, changements de stop, coûts connus, latence, corrélation, provenance et horodatage; un ordre `UNCERTAIN` impose réconciliation avant nouvelle action. Les alertes restent dans un journal même si une notification externe échoue.

## B. Actions et autorisations

Trois niveaux : consulter, préparer, exécuter. Les composants ne décident pas eux-mêmes de l'autorisation : demander à une **façade applicative** l'état des capacités et le résultat du RiskEngine. Un bouton visible en mode `PAPER` ouvre une simulation locale uniquement; un bouton broker `LIVE` ne doit pas être généré ou activé tant que la capacité correspondante et l'autorisation utilisateur ne sont pas établies. Test CFD DEMO borné historique ≠ approbation générale.

Le dialogue de confirmation doit préciser : **source du prix**, environnement, compte, marché, produit exact, direction économique, `order_side`, quantité, stop, TP, KO, frais, perte estimée et éventuelle différence avec la perte maximale KO, timestamp de validation. En contexte `STALE` ou risque non calculable, aucun bouton d'exécution valide.

## C. Gestion des stops

Afficher la valeur *confirmée par le broker* et, si elle diffère, la valeur *proposée/pendante*. Ne pas afficher `Stop sécurisé` tant qu'une confirmation broker (ou mise à jour Paper attestée) ne l'établit. Stop d'un long ne se baisse pas automatiquement; stop d'un short ne monte pas automatiquement. Le break-even « net de frais » ne garantit jamais risque zéro (gap, slippage, défaillance de protection, KO).

## Exigences

- **GUI2-ORD-001** : identités compte/environnement/exécution visibles sur toutes lignes et actions.
- **GUI2-ORD-002** : actualisation prix et PnL non bloquante et âge du prix contrôlé.
- **GUI2-ORD-003** : stop/TP/KO simultanés et différenciés, statut confirmé/proposé/pending.
- **GUI2-ORD-004** : stockage et présentation distincts des positions IG et Paper; aucune agrégation ambiguë.
- **GUI2-ORD-005** : impossibilité pour GUI de contourner le RiskEngine et les droits/permissions API.
- **GUI2-ORD-006** : ordres en attente natifs et locaux clairement séparés; panne/fermeture application détectée.
- **GUI2-ORD-007** : reprise des fonctionnalités Paper vérifiées, sans régression des snapshots/restauration explicite.
- **GUI2-ORD-008** : confirmations/correlation_id/état incertain et journalisation de chaque action.
- **GUI2-ORD-009** : boutons `Modifier`/`Clôturer` désactivés avec explication en l'absence de chemin broker autorisé.
- **GUI2-ORD-010** : shortlist des positions du Dashboard synchronisée avec la même source de vérité.

## Acceptation

En `IG LIVE` données + `PAPER` exécution, la vue doit marquer toutes les positions simulées `PAPER` et les boutons n'appellent jamais `IGRestAdapter.create_otc_position`. Un stop non confirmé ne change pas d'affichage « actif ». Déconnexion avec pendings locaux ⇒ bannière visible. Restauration Paper avec doublon ⇒ confirmation et prévention de l'écrasement, conformément aux règles existantes.
