# Architecture — Refonte GUI V2 par migration incrémentale

**Cible :** Windows / PyQt5 / PyQtGraph / Python 3.12; branche source examinée `chore/sr41-upgrade`, commit `1844916` du 09/11/2026. **Code non modifié par ce PRD.**

## 1. Diagnostic du code de référence (faits vérifiés)

| Emplacement actuel | Observation | Conséquence pour GUI V2 |
|---|---|---|
| `ui/main_window.py` | 3 558 lignes, coordonne IG, flux, scanner, macro, IA, Paper, persistance et layout; `QSplitter` + `QTabWidget`, pas de `QDockWidget` | Extraire l'orchestration et découper les pages; pas de réécriture en une seule PR |
| `ui/chart_view.py` | Chart PyQtGraph en production | **Réutiliser** la vue graphique et ses modèles; ne pas réimplémenter chandeliers/ranges |
| `ui/product_selector.py`, `ticket_view.py`, `paper_portfolio_view.py` | Widgets métier existants | Les encapsuler d'abord dans des pages; remplacer progressivement les tables si nécessaire |
| `ui/scanner_view.py` | `QTableWidget` et calcul de rendu | Passage gradué à `QTableView` + model/proxy pour streaming et catalogue |
| `services/scanner_runtime_batch_service.py` | assemble batch depuis bindings exacts et bougies de session, déclenchement GUI principalement manuel | Découpler scheduling/présentation et afficher chaque marché même incomplet |
| `services/indicator_service.py`, `technical_strategy_service.py`, `scanner_component_service.py` | indicateurs, stratégies, scores déterministes | Rester source de vérité; aucun score redéfini dans des widgets |
| `services/analytics_service.py` | agrégation PnL réalisé jour/semaine/mois/année et par devise | Ajouter projections equity/stats avec provenance; pas de courbe historique sans données |
| `services/paper_session.py`, `paper_broker.py` | exécution locale, save/restore explicitement demandés | Reprendre à l'identique; pas de restaurations automatiques non approuvées |
| `adapters/ig_rest.py` | méthodes générales d'ouverture/modification/clôture IG lèvent `LiveTradingDisabledError` | Les nouveaux boutons d'exécution réels restent interdits |
| `app/config.py::WorkspaceState` | fenêtre largeur/hauteur et taille du splitter | Étendre par migration versionnée avec onglets, géométrie, thème, locale |
| `docs/codex/SR_PACK_VERSION.json` | SR Method 4.1.0 présent | Couvrir les lots par Scope/Verification/Activation, sans plan TDD obligatoire |

**Ne pas déduire des 606 tests signalés localement par Codex que la nouvelle GUI est déjà validée.** Le commit lu n'a pas été exécuté par cet audit; les validations Windows/connexion réelles restent du travail de Codex et de l'utilisateur.

## 2. Règles de dépendances

```text
trading_ig_assistant/
  domain/          # pure, sans Qt ni HTTP ; NE PAS déplacer sans nécessité
  adapters/        # IG REST/Streaming, OpenAI, RSS, calendrier ; conserver
  persistence/     # SQLite, journal, session Paper ; conserver contrats
  services/        # métier existant : indicateurs, scanner, risque, Paper
  app/
    runtime/                 # propriétaire unique du cycle de vie, composants existants injectés
    ui_facade.py             # API de consultation et commandes permises
    projections/             # nouveaux DTO UI construits depuis domain/services
      account_projection.py
      pnl_projection.py
      market_projection.py
      position_projection.py
      health_projection.py
      optimization_projection.py
  ui/
    shell/
      main_window_v2.py     # QMainWindow : composition et navigation seulement
      nav_sidebar.py
      account_header.py
      macro_compact_bar.py
      page_router.py
    pages/
      dashboard_page.py
      scanner_page.py
      watchlist_page.py
      positions_page.py
      analytics_page.py
      macro_ai_page.py
      diagnostics_page.py
      settings_page.py
    models/
      market_table_model.py
      product_table_model.py
      position_table_model.py
      trades_table_model.py
      pnl_series_model.py
    widgets/
      kpi_card.py
      freshness_badge.py
      score_chip.py
      financial_charts.py
      ...                   # wrappers des widgets PyQtGraph et Paper existants
    theme/
      tokens.py
      theme_manager.py
      tradingig_dark.qss
    i18n/
      language_manager.py
      tradingig_fr.ts
      tradingig_en.ts
```

Arborescence **proposée** : conserver les chemins actuels tant qu'un lot n'a pas prouvé qu'il peut migrer les imports et les tests. Ne pas créer des fichiers d'adaptation vides juste pour correspondre au diagramme. Aucun nouveau framework GUI et pas de serveur web.
## 3. `TradingRuntime` et la façade

- `TradingRuntime` (ou application controller équivalent) possède la session IG, les listeners, les timers/schedulers et les services Paper existants. Il crée **une seule** instance de `IGRestAdapter`, `IGStreamingAdapter` par contexte selon l'architecture existante; la navigation de page ne crée ni client ni souscription supplémentaire.
- `UIFacade` expose `get_account_header()`, `subscribe_market_rows()`, `get_positions(scope)`, `get_pnl_series(scope, period)`, `get_macro_events()`, `get_market_analysis(underlying_id)`, `get_health()` sous formes typées, sans PyQt dans le domaine.
- Commands distinctes : `refresh_scanner`, `request_ai_analysis`, `prepare_paper_ticket`, `apply_paper_stop_tightening`, `save_paper_snapshot`, `switch_account`; chaque commande valide scope/capabilities et journalise les conséquences. Le simple rendu d'une page n'appelle jamais une commande.
- Le GUI reçoit des snapshots **immuables avec `generation_id`**; après changement de compte une réponse d'une ancienne génération est ignorée (évitant l'affichage cross-account). Le `QThread` et ses signaux restent côté façade Qt/application bridge.
- Eviter un store qui réplique tout le domaine : une projection de lecture légère suffit si les services existants sont fiables; conserver un seul propriétaire de l'état métier.

## 4. Refactorisation de `MainWindow` sans « big bang »

1. **Geler le comportement** : vérifier la branche propre, les tests unitaires/régression et créer une branche spécifique. Tracer la carte réelle des callbacks/signaux de `main_window.py` et les invariants (IG connect/disconnect, compte, produit, flux, scanner, OpenAI, Paper, persistence).
2. **Introduire le shell V2 hors circuit** (`MainWindowV2`) avec des pages remplaçables et fausses données étiquetées DEMO UI uniquement dans les tests; aucune commande réseau ni ordre.
3. **Brancher header et navigation** sur projections réelles readonly; l'ancienne fenêtre reste accessible par un flag temporaire `--ui legacy|v2` ou configuration dev équivalente sans lancer deux runtimes simultanément.
4. **Extraire un bloc à la fois** : account/profiles, scanner, macro/IA, Paper, sans déplacer les calculs métier et sans changer le format des événements. Ajouter des tests de parité des snapshots avant de supprimer les anciens callbacks.
5. **Migrer les tableaux** nécessitant de fortes mises à jour de `QTableWidget` vers `QAbstractTableModel`, avec `Qt.DisplayRole`, `Qt.ForegroundRole`, `Qt.BackgroundRole`, `Qt.ToolTipRole`, `Qt.UserRole` pour identifiants, `QSortFilterProxyModel`; préserver l'index sélectionné via identifiants.
6. **Reprendre `ChartView` existant** dans la nouvelle Watchlist; préserver les méthodes et événements. Ajouter sous-plots RSI/MACD/ATR uniquement si la structure existante permet un ajout compatible; éviter rebase/remplacement du graphique.
7. **Extraire progressivement les coordinations UI** et retirer l'ancien chemin après parité/validation Windows. Objectif indicatif : `MainWindowV2` devient un assembleur de pages plutôt qu'un module de plusieurs milliers de lignes; la taille en lignes n'est pas un critère isolé de DoD.

**Règle absolue** : aucun refactor d'UI n'est une justification pour activer les méthodes d'ordre dans `IGRestAdapter`. L'application doit rester PAPER/ANALYSIS côté GUI V2.

## 5. Performance / threads

- Les données IG arrivent par listeners/threads existants; tous les `QAbstractTableModel` se mettent à jour **uniquement dans le thread Qt GUI** via événements `QueuedConnection` ou équivalent.
- Grouper les updates (tick coalescing), mettre à jour lignes/cellules changées (`dataChanged`) et non un `resetModel()` complet à chaque prix. Rechercher les goulots si 500+ produits affichés.
- Les requêtes REST, OpenAI, RSS, scraping interdit, accès DB important et validation longue s'exécutent hors GUI thread ; annulation/résultats de génération obsolète maîtrisés.
- Paramètres de fréquence UI (proposés) : header 1 Hz, tables de prix 2-4 Hz, chart 1-4 Hz, analyse technique aux **bougies clôturées**, macro selon TTL autorisé, pas de rafraîchissement des événements sans source.
- Pas d'appels OpenAI de « heartbeat » ; statut IA dérivé de la configuration et des derniers probes réellement consentis.

## 6. Données / sauvegarde / migrations

- Étendre `WorkspaceState` sans casser les JSON existants : version `layout_version=2`, `window_geometry`, `active_page`, `active_subtabs`, `sidebar_collapsed`, `theme`, `locale`, visibility, table column state et éventuel `dock_state` en encodage sûr et contrôlé.
- Garder la migration **idempotente et réversible** ; si des schémas SQLite supplémentaires sont nécessaires pour equity snapshots ou journal d'optimisation, migration testée from-scratch et from-existing, avec sauvegarde et rollback. Aucune migration automatique du journal sans vérification.
- Les snapshots Paper actuels avec checksum et la restauration explicite ne changent pas; une GUI à onglets n'est pas une nouvelle politique de récupération.
- Les **images du PRD** servent de guide esthétique. Des prix/scores/impressions de disponibilité trompeurs dans les mocks ne doivent pas être copiés dans des données réelles.

## 7. Internationalisation de l'architecture

Préparer l'i18n **au lot GUI de fondation** : `LanguageManager`, locale persistée, chaînes de navigation/toolbar dès le premier widget; ne pas ajouter d'abord 50 écrans en français codé dur pour « traduire à la fin ». Les codes métiers restent invariants et les conversions `QLocale` n'affectent pas les calculs numériques.

## 8. Comportements à ne surtout pas modifier sans lot séparé

- Politique OHLC `session-only` : pas de REST-backfill ni réutilisation automatique des caches au démarrage tant que l'utilisateur ne l'a pas validé.
- Flux IG soumis aux droits et quotas par compte / EPIC ; ne pas souscrire tous les 567 produits présents dans le catalogue.
- Binding dérivé EPIC→underlying strict, pas de rapprochement par nom.
- Revue Paper explicite / sécurité des stops / no widen / session save-restore.
- LIVE trades & AUTO désactivés et `LiveTradingDisabledError` conservé.
- Traitement IA consultatif, sources et TTL; pas de déclenchement automatique d'ordres ou de recherche web coûteuse.

## 9. Exigences structurelles

- **GUI2-ARCH-001** : code métier indépendant de PyQt / sources transport; aucune règle de risque dans l'UI.
- **GUI2-ARCH-002** : une seule session et un seul runtime central, sans multiplicateurs d'appels réseau après navigation.
- **GUI2-ARCH-003** : projections typées et identifiées par compte/market/product/mode.
- **GUI2-ARCH-004** : migration incrémentale avec ancien écran en secours jusqu'à validation.
- **GUI2-ARCH-005** : parité du fonctionnel existant démontrée par tests, et non supposée après découpage.
- **GUI2-ARCH-006** : un nouvel onglet ne peut appeler directement ni adapter IG ni keyring ni commande de trading.
- **GUI2-ARCH-007** : découpage Qt threads, coalescing et flux stales correctement gérés.
- **GUI2-ARCH-008** : configuration et persistance rétrocompatibles, sans perte de Paper ou journal.
- **GUI2-ARCH-009** : thème/i18n centralisés et testables séparément des vues métiers.
- **GUI2-ARCH-010** : niveau d'effort et risques du refactor motivés par résultats, pas des déplacements cosmétiques massifs.

## 10. Exemple de frontière de façade (indicatif)

```python
from typing import Protocol
from collections.abc import Callable

class TradingUIFacade(Protocol):
    def read_account_header(self): ...
    def read_dashboard(self, scope, period): ...
    def read_market_rows(self, watchlist_id): ...
    def read_position_rows(self, scope): ...
    def read_health(self): ...
    def request_refresh(self, section: str) -> None: ...
    def subscribe(self, kind: str, on_snapshot: Callable) -> object: ...

# Never add:  def place_live_order_from_button(self, ...): ...
```

Dans le code effectif, remplacer `...` par des types réutilisant les classes `domain`; garder la façade distincte de la classe `QMainWindow`. Les commandes Paper utilisent le service existant et les gates explicites.
