# Product Brief — IG Trading Assistant

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](decisions.md) apply. Earlier project text is preserved; explicit V1.2 changes take precedence only on documented conflicts. This is not implementation or activation evidence.


> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-10-22

## Problem statement
The user trades IG Barriers/Options manually on instruments such as US Tech 100, France 40, Germany 40, and Spot Gold. The current workflow relies on reading the IG web platform, manually estimating the best trade, selecting a barrier/option, entering quantity/stop/limit, and then manually adjusting the stop after the trade starts moving.

This creates recurring issues:
- entry decisions can be emotional after a winning or losing trade;
- position size can become too aggressive;
- follow-up trades may be opened without checking total exposure;
- stop management is manual and can be late or inconsistent;
- barriers/options do not always expose a convenient delayed-order workflow in the web UI;
- market context from macro/geopolitical news is separate from the technical chart view and is not visible as a compact control/status band during trade preparation.

The product solves this by building a disciplined assistant connected to IG APIs that provides market data, charting, product selection, risk-controlled ticket generation, software pending-order monitoring, dynamic stop management, and journaling.

## Target users / personas
- **Primary user:** Stéphane, technically advanced retail trader, comfortable with Python/PyQt, wants precise control and transparent logic rather than a black-box robot.
- **Secondary future user:** technically literate trader who wants a local desktop trading assistant for IG products with strict risk management and manual confirmation.

## Goals
- **G1:** Connect reliably to IG demo/live environments via REST and Streaming APIs.
- **G2:** Allow the user to choose from available IG Barrier/Option contracts and inspect their constraints before building a ticket.
- **G3:** Display IG-like candlestick charts with trade overlays and real-time updates.
- **G4:** Analyze a small watchlist and rank trade opportunities by technical setup quality and market context.
- **G4b:** Display a persistent Global Market Context Ribbon below the main menu, using red/yellow/green/gray indicators for macro, geopolitical, rate, dollar, oil, volatility and data-health signals.
- **G5:** Generate a complete ticket: instrument/product, direction, quantity, knock-out/barrier, stop, limit, expected loss, target gain, R/R ratio, fees/prime where available.
- **G6:** Provide software pending-order logic for manual assisted entry when native delayed orders are not available or not suitable for the selected product.
- **G7:** Monitor open trades and manage stop updates through deterministic state-machine rules.
- **G8:** Journal every trade, action, recommendation, decision, and outcome for later analysis and backtesting.

## Non-goals
- **NG1:** The MVP is not a fully autonomous live trading robot.
- **NG2:** The app does not guarantee profitable trades and MUST NOT label any trade as risk-free.
- **NG3:** The app does not replace the IG platform; it assists, validates, and optionally invokes supported API actions.
- **NG4:** The MVP does not implement complex machine learning or opaque AI-based execution.
- **NG5:** The macro/news module does not provide legally regulated investment advice; it provides context and risk flags.

## Scope by phase
### P00 Bootstrap
- Create Python project skeleton.
- Implement settings model and secure credential storage abstraction.
- Validate IG demo authentication.
- Retrieve account metadata and market snapshots.
- Record a technical spike about Barriers/Options API support and limitations.

### P20 Architecture
- Implement REST/Streaming boundaries.
- Implement domain models: Instrument, ProductContract, Candle, Quote, Ticket, Position, PendingOrder, TradeState, JournalEvent.
- Implement event bus and persistence layer.

### MVP (P30)
- IG connection configuration screen.
- Product discovery/selection for configured instruments and available Barrier/Option contracts.
- Real-time candle chart with IG-like overlays.
- Watchlist scanner and setup scoring.
- Macro/news context panel and persistent Global Market Context Ribbon.
- Ticket builder and risk validation.
- Software pending-order monitor with manual confirmation.
- Trade monitor with break-even and trailing-stop recommendations or updates where supported.
- Journal and basic analytics.

### V2+
- Optional semi-automated order placement if API support is confirmed and explicitly enabled.
- Advanced chart tools and multi-timeframe analysis.
- ATR/structure-based trailing modes.
- Replay and backtesting of trade-management rules.
- Configurable provider adapters for economic calendar/news.
- Alerting via desktop notification, email, Telegram, or MQTT.

## Constraints
- Python desktop application; PyQt/PySide + pyqtgraph or equivalent charting stack are preferred.
- The user is technically advanced and values modular, testable, object-oriented code.
- IG API coverage for Barriers/Options must be verified early; fall back to manual assisted workflows when an API action is unsupported.
- Demo mode must be supported before live mode.
- API credentials must be configured in the UI but stored securely using OS keyring or equivalent encrypted storage.
- No secrets in repository, logs, journal exports, or screenshots.
- Risk engine must be independent from UI so it can be unit-tested and backtested.

## Success criteria
See `01_product/kpis.md`.

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 1; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-1"></a>

## 1. Vision, objectif et frontières

### 1.1 Vision

Construire une **station locale de trading assisté, supervisé puis automatisé**, capable de surveiller plusieurs marchés, sélectionner et expliquer des opportunités à court terme, préparer des ordres compatibles avec le courtier, gérer les positions et enregistrer toutes les décisions. La plateforme doit rester multi-courtiers par architecture, même si IG est l'unique courtier opérationnel au départ.

**Horizon des trades :** quelques minutes à quelques heures, principalement intraday. Aucun volume minimal de transactions imposé au moteur : `NO_TRADE` est un résultat normal et souhaitable lorsque les conditions sont défavorables.

### 1.2 Objectifs produit

1. Exploiter **IG CFD** et **IG Barrières/Options**, avec une vue consolidée et des contraintes propres à chaque compte/produit.
2. Acquisition OHLC/quotes fiable : **historique initial mesuré + cache local + streaming continu**, indépendante des ordres.
3. Scanner configurable multi-marchés et multi-stratégies, avec score, risque, gain espéré, **commentaire de justification** et statut explicite.
4. Stratégies initiales : **trend following, breakout, pullback et événements** ; indicateurs techniques configurables et contexte/sentiment de marché.
5. Trading en **trois modes** : analyse seule, ordre supervisé, ordre automatique (désactivé par défaut).
6. **Gestion dynamique** : stop, take profit, passage à l'équilibre net, sécurisation de profit, trailing et clôture suivant règles.
7. **Risque paramétrable** : valeurs initiales 1 % par transaction, 3 % de drawdown journalier, 1 position globale et 1 position par sous-jacent, règles tenant compte des expositions sur plusieurs comptes.
8. Interface Windows multipanneaux, onglets, statistiques P&L et diagnostics, fonctionnement continu tant que l'application est ouverte.
9. Recorder de recherche conservant autant les signaux non exécutés que les trades réalisés ; backtest/replay puis validation quantitative des modèles IA.
10. Notifications choisies dans l'interface : Windows, e-mail, Telegram et, indirectement, téléphone via ces canaux.

### 1.3 Hors périmètre de la première livraison utilisable

- Aucun rendement garanti ou objectif de rentabilité contractuel.
- Aucun LLM finement entraîné comme prérequis pour trader.
- Aucun service Windows, déploiement Linux, web app distante ou application mobile native en V1.
- Aucun scrapping de TradingView ou contournement de son mode d'accès aux données ; intégration uniquement via interfaces officiellement utilisables/licenciées.
- Aucune exécution live tant que l'API IG, le contrôle du compte, les tests d'ordres, la réconciliation et les garde-fous n'ont pas été validés.
- Aucun calcul de P&L estimé présenté comme exact s'il manque cours de sortie, taux FX, frais ou financement.

### 1.4 Indicateurs de réussite (mesurables)

- **Intégrité marché :** zéro bougie M5 incorrecte sur la suite de fixtures M1 de référence ; aucun doublon logique OHLC après redémarrage.
- **Sécurité :** zéro ordre réel dans les modes Analyse/Paper ; toutes les commandes sont rattachées à un compte explicite ; aucune réémission automatique après réponse inconnue.
- **Traçabilité :** 100 % des propositions, autorisations, refus, commandes et transitions de position produisent des événements horodatés.
- **Disponibilité :** état de connexion, fraîcheur et capacité des API toujours visibles ; une interruption ne doit pas être masquée comme « connecté ».
- **Qualité des modèles :** toute stratégie/IA est comparée à un baseline hors échantillon, nette de coûts, avant admission au mode automatique.
- **UX :** ouverture des onglets et manipulation du graphique sans bloquer sur une requête réseau ; paramètres persistés et restaurés.
