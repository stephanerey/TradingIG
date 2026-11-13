"""Stable message IDs used by the initial GUI V2 shell."""

CATALOGS: dict[str, dict[str, str]] = {
    "fr_FR": {
        "app.title": "TradingIG — Analyse et Simulation",
        "nav.dashboard": "Tableau de bord",
        "nav.scanner": "Marchés / Scanner",
        "nav.watchlist": "Valeurs suivies",
        "nav.positions": "Positions et ordres",
        "nav.history": "Historique / Analyses",
        "nav.macro": "Macro / IA",
        "nav.diagnostics": "Diagnostics",
        "nav.settings": "Paramètres",
        "nav.collapse": "Réduire la navigation",
        "nav.expand": "Déployer la navigation",
        "header.account": "Compte",
        "header.no_account": "Aucun compte",
        "header.environment": "Environnement",
        "header.execution": "Mode",
        "header.data": "Données",
        "header.ai": "IA",
        "header.connect": "Connecter",
        "header.connecting": "Connexion…",
        "header.connected": "Connecté ✓",
        "header.disconnect_action": "Déconnecter",
        "header.connect_help": "Ouvrir une session IG en lecture seule.",
        "header.connected_help": "Session IG connectée. Cliquez pour déconnecter.",
        "header.read_only_safety": (
            "{environment} · SIMULATION · aucun ordre IG"
        ),
        "header.account_family_cfd": "CFD",
        "header.account_family_options": "BARRIÈRES & OPTIONS",
        "header.account_family_spreadbet": "SPREAD BET",
        "header.account_family_shares": "ACTIONS",
        "header.account_family_unknown": "COMPTE IG",
        "header.account_connect_first": "Aucun compte — connectez DEMO ou LIVE",
        "header.account_selector_help": (
            "Comptes de l’environnement IG connecté. Pour changer entre DEMO et LIVE, "
            "déconnectez d’abord la session active."
        ),
        "header.account_metrics_unavailable": (
            "Equity IG : N/A · Solde : N/A · Disponible : N/A · PnL : N/A"
        ),
        "header.account_metrics": (
            "Equity IG : {equity} · Solde : {balance} · Disponible : {available} · PnL : {pnl}"
        ),
        "header.account_metrics_tooltip": "Données compte REST/flux reçues à {timestamp}",
        "header.metric.equity": "Equity IG",
        "header.metric.balance": "Solde",
        "header.metric.available": "Disponible",
        "header.metric.pnl": "PnL IG",
        "status.analysis": "ANALYSE",
        "status.paper": "SIMULATION",
        "status.disconnected": "Déconnecté",
        "status.not_configured": "Non configurée",
        "status.ai.not_configured": "non configurée",
        "status.ai.configured": "configurée · lancement manuel",
        "status.ai.running": "analyse en cours",
        "status.ai.ready": "dernière analyse disponible",
        "status.ai.stale": "dernière analyse périmée",
        "status.unavailable": "Indisponible",
        "status.unknown": "Inconnu",
        "connection.busy": "Une opération de connexion est déjà en cours.",
        "connection.already_connected": "Un compte IG est déjà connecté.",
        "connection.profile_missing.demo": "Configurez d’abord le profil IG DEMO.",
        "connection.profile_missing.live": "Configurez d’abord le profil IG LIVE.",
        "connection.store_unavailable": "Le coffre de clés système est indisponible.",
        "connection.credentials_missing.demo": "Les identifiants DEMO sont absents du coffre.",
        "connection.credentials_missing.live": "Les identifiants LIVE sont absents du coffre.",
        "connection.not_connected": "Aucun compte IG n’est connecté.",
        "connection.account_unknown": "Ce compte n’appartient pas à la session active.",
        "connection.invalid_result": "La connexion a renvoyé un résultat invalide.",
        "connection.session_token_invalid": (
            "IG a refusé deux jetons de session successifs. Attendez environ une minute, puis "
            "reconnectez-vous. Les identifiants et la clé API ont bien été acceptés."
        ),
        "connection.config_save_failed": (
            "Le compte est connecté, mais le profil n’a pas pu être enregistré."
        ),
        "connection.closing": "Fermeture après la fin de l’opération de connexion…",
        "dashboard.scope.unavailable": (
            "Simulation indisponible — aucune donnée inventée"
        ),
        "dashboard.scope.paper": "SIMULATION · {account} · projection {timestamp}",
        "dashboard.kpi.equity": "Equity",
        "dashboard.kpi.balance": "Solde compte IG",
        "dashboard.kpi.available": "Fonds disponibles",
        "dashboard.kpi.account_pnl": "PnL courant IG",
        "dashboard.kpi.margin": "Dépôt / marge IG",
        "dashboard.kpi.day_pnl": "PnL réalisé jour",
        "dashboard.kpi.week_pnl": "PnL réalisé semaine",
        "dashboard.kpi.month_pnl": "PnL réalisé mois",
        "dashboard.kpi.positions": "Positions simulées ouvertes",
        "dashboard.kpi.win_rate": "Taux de réussite",
        "dashboard.kpi.profit_factor": "Profit factor",
        "dashboard.kpi.drawdown": "Drawdown",
        "dashboard.positions.title": "Positions simulées ouvertes — lecture seule",
        "dashboard.positions.empty": "Aucune position simulée ouverte dans cette session.",
        "dashboard.performance.unavailable": "Historique de simulation indisponible.",
        "dashboard.performance.no_equity_history": (
            "Aucune courbe equity n’est affichée : aucun snapshot historique attesté. "
            "Les totaux ci-dessous, s’ils existent, sont uniquement du PnL réalisé."
        ),
        "dashboard.performance.period.day": "Jour",
        "dashboard.performance.period.week": "Semaine",
        "dashboard.performance.period.month": "Mois",
        "dashboard.performance.period.year": "Année",
        "dashboard.performance.mode.currency": "Montant réalisé",
        "dashboard.performance.mode.percent": "% du capital initial",
        "dashboard.performance.no_realized_pnl": (
            "Aucun PnL réalisé attesté pour cette période et cette devise."
        ),
        "dashboard.performance.percent_unavailable": (
            "N/A : aucun capital initial horodaté ne permet un pourcentage attesté."
        ),
        "dashboard.performance.realized_scope": (
            "PnL simulé réalisé · {currency} · {count} clôture(s) attestée(s)."
        ),
        "dashboard.ai.unavailable": (
            "Aucune proposition IA attestée. Rien n’est généré ni appliqué automatiquement."
        ),
        "dashboard.position.product": "Produit",
        "dashboard.position.direction": "Sens",
        "dashboard.position.quantity": "Quantité",
        "dashboard.position.entry": "Entrée",
        "dashboard.position.mark": "Prix valorisé",
        "dashboard.position.pnl": "PnL net estimé",
        "dashboard.position.stop": "Stop confirmé",
        "dashboard.position.status": "État",
        "catalogue.search": "Compléter depuis IG",
        "catalogue.follow": "Ajouter aux valeurs suivies",
        "catalogue.query_placeholder": "Filtrer le catalogue à la volée…",
        "catalogue.empty": "Aucun inventaire local disponible. La navigation n’appelle pas IG.",
        "catalogue.inventory": (
            "Catalogue : {count} produit(s) · {visible} visible(s) · inventaire local "
            "{timestamp}. La saisie filtre localement sans appel IG."
        ),
        "catalogue.results": (
            "{visible}/{count} produit(s) visible(s) · dernier complément IG « {query} » · "
            "snapshot {timestamp}."
        ),
        "catalogue.analysis_unavailable": (
            "Analyse indisponible : aucune bougie clôturée attestée dans le runtime V2."
        ),
        "scanner.status.unavailable": "Scanner indisponible — aucune donnée inventée.",
        "scanner.status.summary": (
            "{visible}/{configured} marché(s) affiché(s) · état {state} · projection "
            "{timestamp}. Les scores restent INCONNU jusqu’aux bougies de session attestées."
        ),
        "scanner.column.market": "Marché de référence",
        "scanner.column.asset": "Classe",
        "scanner.column.last": "Dernier",
        "scanner.column.change": "Variation",
        "scanner.column.freshness": "Source / âge",
        "scanner.column.technical": "Technique",
        "scanner.column.context": "Contexte",
        "scanner.context.unknown": "INCONNU",
        "scanner.context.catalyst": "CATALYSEUR",
        "scanner.context.aligned": "ALIGNÉ",
        "scanner.context.caution": "PRUDENCE",
        "scanner.context.unfavorable": "DÉFAVORABLE",
        "scanner.context.no_evidence": (
            "Aucun contexte macro/IA attesté et applicable à ce produit."
        ),
        "scanner.context.veto_yes": "oui",
        "scanner.context.veto_no": "non",
        "scanner.context.tooltip": (
            "Contexte indicatif uniquement — ni recommandation, ni probabilité.\n"
            "Composants :\n{components}\nVeto sécurité : {veto}\n"
            "Raisons : {reasons}\nProvenance : {provenance}"
        ),
        "scanner.column.direction": "Direction",
        "scanner.column.decision": "Décision",
        "scanner.column.reason": "Raison",
        "scanner.column.evaluated": "Évalué à",
        "scanner.direction.unknown": "INCONNU",
        "scanner.direction.bullish": "HAUSSIER",
        "scanner.direction.bearish": "BAISSIER",
        "scanner.direction.neutral": "NEUTRE",
        "scanner.decision.unavailable": "INDISPONIBLE",
        "scanner.decision.candidate": "OPPORTUNITÉ",
        "scanner.decision.watch": "À SURVEILLER",
        "scanner.decision.no_trade": "NO_TRADE",
        "scanner.reason.session_ohlc_warming_up": ("Bougies de session : {observed}/{required}"),
        "scanner.reason.analysis_pending": "Analyse en attente ({observed} bougies)",
        "scanner.reason.no_confirmed_breakout": "Aucune cassure confirmée",
        "watchlist.analysis_pending": (
            "Analyse consultative en attente de données attestées suffisantes. "
            "Aucun ticket ni ordre n’est créé depuis cette vue."
        ),
        "watchlist.no_market": "Aucun marché de référence sélectionné.",
        "watchlist.no_product": "Aucun produit suivi",
        "watchlist.remove_product": "Retirer de la liste",
        "watchlist.technical.summary": (
            "{market} · Direction {direction} · Décision {decision} · "
            "Technique {technical} · Contexte {context}\n"
            "Bougies clôturées observées : {observed}/{required} · Évalué : {evaluated}\n"
            "Raisons : {reasons}. Les scores sont des rangs explicables, pas des probabilités."
        ),
        "watchlist.technical.product_fallback": (
            "Source de repli : bougies M1 construites depuis les cotations PRICE du produit "
            "exact ; elles ne sont pas présentées comme le graphique du sous-jacent."
        ),
        "watchlist.signal.strategy": "Stratégie",
        "watchlist.signal.product": "Produit",
        "watchlist.signal.direction": "Signal",
        "watchlist.signal.state": "Données",
        "watchlist.signal.entry": "Entrée",
        "watchlist.signal.invalidation": "Inv.",
        "watchlist.signal.target": "Obj.",
        "watchlist.signal.valid_until": "Expiration",
        "watchlist.technical.no_signal": (
            "Aucun signal de stratégie attesté n’est disponible pour ce marché."
        ),
        "watchlist.technical.detail": (
            "Signal : {signal_id} · Confiance : {confidence} · Qualité : {quality}\n"
            "Généré : {generated} · Valide jusqu’à : {valid_until}\n"
            "Raisons : {reasons}\nProvenance : {provenance}\n"
            "Caractéristiques attestées :\n{features}"
        ),
        "watchlist.plan.long": "Scénario haussier / LONG",
        "watchlist.plan.short": "Scénario baissier / SHORT",
        "watchlist.plan.no_trade": "NO_TRADE / Blocages",
        "watchlist.plan.unavailable": (
            "{direction} — aucun signal READY attesté. Aucune proposition n’est déduite."
        ),
        "watchlist.plan.scenario": (
            "{direction} · {strategy}\nProduit de preuve : {product}\n"
            "Entrée : {entry} · Invalidation : {invalidation} · Objectif : {target}\n"
            "Valide jusqu’à : {validity}\n"
            "Direction de marché uniquement ; aucun sens d’ordre IG n’est déduit."
        ),
        "watchlist.plan.blockers": (
            "Décision scanner : {decision}\nBlocages : {blockers}\n"
            "Aucun ticket ni ordre n’est généré depuis ce résumé."
        ),
        "chart.overlay.entry_min": "Entrée−",
        "chart.overlay.entry_max": "Entrée+",
        "chart.overlay.invalidation": "Inv.",
        "chart.overlay.target": "Obj.",
        "chart.overlay.fast_ema": "EMA R",
        "chart.overlay.slow_ema": "EMA L",
        "chart.overlay.support": "Sup.",
        "chart.overlay.resistance": "Rés.",
        "watchlist.overlay.title": "Signal affiché :",
        "watchlist.overlay.signal_option": "{strategy} · {direction} · {state}",
        "watchlist.overlay.signal_selector_tooltip": (
            "Choisissez la stratégie projetée sur le graphique. La ligne correspondante "
            "est sélectionnée dans Analyse technique ; les autres indicateurs prêts ne "
            "sont pas superposés à ce signal."
        ),
        "watchlist.overlay.entry": "Zone d’entrée",
        "watchlist.overlay.invalidation": "Invalidation",
        "watchlist.overlay.target": "Objectif",
        "watchlist.overlay.ema": "EMA",
        "watchlist.overlay.rsi": "RSI",
        "watchlist.overlay.structure": "Support / Résistance",
        "watchlist.overlay.indicator_panel": "Sous-graphe :",
        "watchlist.overlay.indicator_panel_tooltip": (
            "Un seul indicateur à échelle propre est affiché sous le prix."
        ),
        "watchlist.panel.none": "Aucun",
        "chart.panel.rsi.oversold": "Survente",
        "chart.panel.rsi.overbought": "Surachat",
        "chart.panel.macd.line": "MACD",
        "chart.panel.macd.signal": "Signal",
        "chart.panel.macd.histogram": "Histogramme",
        "watchlist.overlay.availability_tooltip": (
            "Une case est active uniquement si le signal sélectionné produit cette donnée."
        ),
        "watchlist.indicators.unavailable": (
            "Indicateurs : sélectionnez un signal technique attesté."
        ),
        "watchlist.indicators.snapshot": (
            "Instantané M1 du signal {strategy} · ATR : {atr} · RSI : {rsi}. "
            "Les courbes historiques ne sont pas inventées."
        ),
        "watchlist.indicators.snapshot_detailed": (
            "Signal affiché {strategy} · données utilisables par ce signal : {values}. "
            "Les autres indicateurs prêts pour le marché restent visibles dans l’onglet "
            "Analyse technique, mais ne sont pas appliqués à ce signal."
        ),
        "watchlist.indicators.none_for_signal": "aucun indicateur numérique disponible",
        "watchlist.indicators.atr": "ATR",
        "watchlist.indicators.rsi": "RSI",
        "watchlist.indicators.fast_ema": "EMA rapide",
        "watchlist.indicators.slow_ema": "EMA lente",
        "watchlist.indicators.support": "Support",
        "watchlist.indicators.resistance": "Résistance",
        "watchlist.indicators.heading": (
            "Indicateurs prêts pour le marché — toutes stratégies actives"
        ),
        "watchlist.indicator.column.name": "Indicateur",
        "watchlist.indicator.column.value": "Valeur",
        "watchlist.indicator.column.params": "Param.",
        "watchlist.indicator.column.state": "État",
        "watchlist.indicator.column.candles": "Bougies",
        "watchlist.indicator.column.source": "Source",
        "watchlist.indicator.state.ready": "PRÊT",
        "watchlist.indicator.state.warming_up": "CHAUFFE",
        "watchlist.indicator.state.invalid": "INVALIDE",
        "watchlist.indicator.name.ema": "EMA",
        "watchlist.indicator.name.atr": "ATR",
        "watchlist.indicator.name.rsi": "RSI",
        "watchlist.indicator.name.recent_levels": "Niveaux récents",
        "watchlist.indicator.name.volume_ratio": "Ratio volume",
        "watchlist.indicator.component.support": "Support",
        "watchlist.indicator.component.resistance": "Résistance",
        "watchlist.indicator.tooltip": (
            "Raisons : {reasons}\nProvenance :\n{provenance}"
        ),
        "watchlist.ai.unavailable": (
            "UNKNOWN — aucune analyse IA spécifique et attestée n’est associée à {market} "
            "({epic}) dans cette session. Ouvrir Macro / IA permet un appel consultatif manuel "
            "avec consentement ; changer d’onglet ne déclenche aucun appel OpenAI."
        ),
        "watchlist.ai.unavailable_reasons": (
            "Raisons : {reasons}. Vérifiez les sources puis lancez manuellement une analyse "
            "consultative depuis Macro / IA."
        ),
        "watchlist.ai.scope_global": "contexte global de marché",
        "watchlist.ai.scope_mismatch": (
            "{market} — la dernière analyse IA est hors périmètre (portée : {scope})."
        ),
        "watchlist.ai.scope_mismatch_detail": (
            "Aucun biais propre à cette valeur n’est déduit d’une analyse portant sur un autre "
            "instrument. Ouvrez Macro / IA pour examiner ou relancer l’analyse."
        ),
        "watchlist.ai.stale": (
            "{market} — analyse consultative périmée ({scope}). Générée : {generated} · "
            "valide jusqu’à : {valid_until}. Relancez l’analyse avant toute interprétation."
        ),
        "watchlist.ai.summary": (
            "{market} — analyse consultative ({scope})\n"
            "Biais : {bias} · risque événementiel : {risk} · indice interne non calibré : "
            "{confidence}\n"
            "Générée : {generated} · valide jusqu’à : {valid_until}\n"
            "Synthèse : {summary}\nDrapeaux : {flags}\n"
            "Une portée globale décrit le contexte commun et non un biais propre à cette "
            "valeur. Cette analyse n’est ni un ordre ni une probabilité de réussite."
        ),
        "watchlist.ai.sources": "Sources utilisées ({count}) :\n{sources}",
        "watchlist.ai.open_macro": "Ouvrir Macro / IA",
        "watchlist.history.session_only": (
            "Historique strictement limité à cette session · EPIC {epic}\n"
            "Bougies M1 observées : {candles} · Première : {first} · Dernière : {last}\n"
            "Aucun historique IG, backtest ou trade n’est inventé ou rechargé automatiquement."
        ),
        "positions.safety": (
            "Lecture seule · positions simulées locales séparées des données broker IG · "
            "aucune action de modification ou clôture disponible."
        ),
        "positions.broker_unavailable": (
            "Données broker positions/ordres non chargées dans le runtime V2. "
            "Aucune donnée n’est simulée."
        ),
        "positions.paper_empty": "Aucune position simulée ouverte dans cette session.",
        "positions.pending_unavailable": (
            "Aucun ordre broker en attente n’est chargé dans la V2. Aucune donnée n’est simulée."
        ),
        "positions.order_history_unavailable": (
            "Historique des ordres broker non chargé. Le journal de simulation local reste "
            "disponible "
            "dans Historique / Analyses."
        ),
        "positions.alerts_empty": (
            "Aucune alerte locale observée dans cette session. L’inbox persistante et les "
            "notifications externes ne sont pas encore activées."
        ),
        "paper.save": "Sauvegarder la simulation",
        "paper.restore": "Restaurer la dernière session",
        "paper.local_only": "Stockage local uniquement — aucune transmission à IG.",
        "paper.save_empty": "Aucun état de simulation à sauvegarder.",
        "paper.save_succeeded": "Session de simulation sauvegardée localement.",
        "paper.save_failed": "Sauvegarde de la simulation refusée : {detail}",
        "paper.restore_missing": "Aucune base de simulation locale à restaurer.",
        "paper.restore_empty": "La base locale ne contient aucune sauvegarde de simulation.",
        "paper.restore_succeeded": (
            "Dernière session de simulation restaurée localement — aucune transmission à IG."
        ),
        "paper.restore_failed": "Restauration de la simulation refusée : {detail}",
        "paper.restore_title": "Restaurer la session de simulation",
        "paper.restore_question": (
            "Remplacer la session de simulation locale courante par la dernière sauvegarde ?"
        ),
        "paper.stop": "Resserrer le stop simulé",
        "paper.stop_title": "Stop simulé local",
        "paper.stop_question": "Nouveau niveau de stop :",
        "paper.stop_invalid": "Niveau de stop invalide.",
        "paper.stop_succeeded": "Stop simulé local mis à jour et attesté.",
        "paper.stop_failed": "Mise à jour du stop simulé refusée : {detail}",
        "paper.close": "Clôturer la position simulée",
        "paper.close_title": "Clôturer la position simulée",
        "paper.close_question": (
            "Clôturer localement la position {position_id} au dernier prix exécutable ?"
        ),
        "paper.close_succeeded": "Position simulée clôturée localement.",
        "paper.close_failed": "Clôture simulée refusée : {detail}",
        "paper.open_title": "Confirmer l’ouverture simulée locale",
        "paper.open_question": (
            "Ouvrir cette position dans la session de simulation locale uniquement ?\n\n"
            "Produit exact : {product}\nMarché canonique : {underlying}\n"
            "Sens d’ordre : {direction}\nQuantité : {quantity}\nEntrée simulée : {entry}\n"
            "Stop : {stop}\nObjectif : {target}\nKO : {knockout}\n"
            "Perte estimée : {loss} {currency}\nCoûts estimés : {costs} {currency}\n"
            "Source prix : {source}\nHorodatage : {timestamp}\n\n"
            "Cette action n’envoie aucun ordre à IG."
        ),
        "paper.open_succeeded": "Position ouverte dans la session de simulation locale.",
        "paper.open_invalid": "Soumission de simulation invalide.",
        "paper.open_stale": "Ouverture simulée refusée : la cotation a expiré.",
        "paper.open_expired": "Ouverture simulée refusée : le brouillon a expiré.",
        "paper.open_failed": "Ouverture simulée refusée : {detail}",
        "paper.ticket.preparation_safety": (
            "Préparation en mode simulation. Le produit IG exact, son binding canonique et une "
            "cotation temps réel fraîche sont obligatoires. L’ouverture locale exige une "
            "évaluation RiskEngine puis une confirmation explicite ; aucun ordre n’est envoyé à IG."
        ),
        "paper.ticket.select_product": (
            "Double-cliquez un produit exact dans Catalogue IG pour préparer son contrôle."
        ),
        "paper.ticket.ready": (
            "PRÊT POUR PRÉPARATION — identité, binding et cotation sont attestés. "
            "La confirmation de simulation locale reste obligatoire."
        ),
        "paper.ticket.prepare_draft": "Préparer le brouillon simulé",
        "paper.ticket.back_to_evidence": "Revenir aux contrôles",
        "paper.ticket.blocked": "{status} — la préparation de simulation est bloquée.",
        "paper.ticket.field": "Contrôle",
        "paper.ticket.value": "Valeur attestée",
        "paper.ticket.product": "Produit",
        "paper.ticket.product_epic": "EPIC produit exact",
        "paper.ticket.product_type": "Type de produit",
        "paper.ticket.underlying": "Marché canonique",
        "paper.ticket.reference_epic": "EPIC de référence",
        "paper.ticket.binding_provenance": "Provenance du binding",
        "paper.ticket.metadata_source": "Source des métadonnées",
        "paper.ticket.currency": "Devise",
        "paper.ticket.deal_constraints": "Contraintes produit",
        "paper.ticket.bid_offer": "Bid / Offer",
        "paper.ticket.market_status": "État du marché",
        "paper.ticket.quote_source": "Source / réception",
        "paper.ticket.blocker": "Blocage",
        "paper.ticket.reason.EXACT_PRODUCT_BINDING_REQUIRED": (
            "Binding exact produit→marché absent ; aucune déduction par nom ou EPIC"
        ),
        "paper.ticket.reason.PRODUCT_TYPE_UNKNOWN": "Type de produit inconnu",
        "paper.ticket.reason.PRODUCT_CURRENCY_UNAVAILABLE": "Devise produit indisponible",
        "paper.ticket.reason.BID_OFFER_UNAVAILABLE": "Bid/Offer indisponible",
        "paper.ticket.reason.BID_OFFER_INVALID": "Bid/Offer invalide",
        "paper.ticket.reason.MARKET_NOT_CONFIRMED_TRADEABLE": (
            "Marché non confirmé TRADEABLE"
        ),
        "paper.ticket.reason.LIVE_QUOTE_REQUIRED": "Cotation Lightstreamer requise",
        "paper.ticket.reason.LIVE_QUOTE_STALE": "Cotation temps réel périmée",
        "paper.ticket.reason.BROKER_DELAYED": "Cotation broker différée",
        "diagnostics.service": "Service",
        "diagnostics.state": "État",
        "diagnostics.summary": "Résumé",
        "diagnostics.observed": "Observé à",
        "diagnostics.reasons": "Raisons",
        "diagnostics.service.ig-rest": "IG REST",
        "diagnostics.service.ig-streaming": "IG Streaming",
        "diagnostics.service.openai": "OpenAI",
        "diagnostics.service.paper-sqlite": "SQLite / simulation",
        "diagnostics.service.official-news": "Actualités officielles",
        "diagnostics.status.ready": "PRÊT",
        "diagnostics.status.warming_up": "EN ATTENTE",
        "diagnostics.status.stale": "PÉRIMÉ",
        "diagnostics.status.unavailable": "INDISPONIBLE",
        "diagnostics.status.not_applicable": "NON APPLICABLE",
        "diagnostics.summary.connected": "Connecté",
        "diagnostics.summary.connecting": "Connexion en cours",
        "diagnostics.summary.disconnected": "Déconnecté",
        "diagnostics.summary.live": "Flux actif",
        "diagnostics.summary.not_configured": "Non configuré",
        "diagnostics.summary.empty_session": "Session locale vide",
        "diagnostics.summary.unsaved_changes": "Modifications non sauvegardées",
        "diagnostics.summary.snapshot_saved": "Snapshot sauvegardé",
        "diagnostics.summary.error": "Erreur de persistance",
        "diagnostics.summary.metadata_available": "Métadonnées disponibles",
        "diagnostics.summary.not_collected": "Collecte non lancée",
        "diagnostics.summary.configured": "Configuré — action manuelle requise",
        "diagnostics.summary.last_request_available": "Dernière analyse disponible",
        "diagnostics.summary.last_request_stale": "Dernière analyse périmée",
        "diagnostics.summary.ready": "Prêt",
        "diagnostics.summary.running": "Analyse en cours",
        "diagnostics.no_active_probe": (
            "Aucune sonde active n’est lancée depuis cette page. "
            "Seuls les événements réellement observés sont présentés."
        ),
        "settings.connections_summary": (
            "Environnement configuré : {environment}\nMode lecture seule : activé\n"
            "Trading LIVE/AUTO : désactivé et non activable depuis la GUI V2."
        ),
        "settings.markets_summary": "{bindings} binding(s) produit/marché exact(s) configuré(s).",
        "settings.strategies_summary": (
            "Seuil opportunité : {candidate}/100\nSeuil surveillance : {watch}/100\n"
            "Les changements de stratégie ne sont pas exposés dans ce lot."
        ),
        "settings.risk_summary": (
            "Les protections existantes restent actives. Aucun réglage de risque n’est "
            "modifié automatiquement."
        ),
        "settings.ai_summary": (
            "IA consultative uniquement. Aucun appel externe ni modification de paramètre "
            "sans consentement explicite."
        ),
        "settings.notifications_summary": "Notifications avancées non configurées.",
        "settings.advanced_summary": (
            "Configuration avancée en lecture seule dans ce lot. "
            "Les secrets ne sont jamais affichés."
        ),
        "history.period": "Période",
        "history.period_key": "Clé",
        "history.amount": "PnL réalisé",
        "history.events": "Événements",
        "history.journal_scope": (
            "Journal append-only de la session de simulation locale. Les payloads internes ne sont "
            "pas exposés dans cette vue."
        ),
        "history.journal_filter": "Filtrer par événement, marché ou corrélation…",
        "history.timestamp": "Horodatage",
        "history.event_type": "Événement",
        "history.instrument": "Instrument",
        "history.correlation": "Corrélation",
        "history.pnl": "PnL",
        "history.pnl_status": "Statut PnL",
        "history.statistics_scope": (
            "Clôtures simulées réalisées et attestées uniquement. Les devises ne sont jamais "
            "fusionnées ; un échantillon réduit reste exploratoire."
        ),
        "history.metric": "Métrique",
        "history.value": "Valeur",
        "history.win_rate": "Taux de réussite",
        "history.profit_factor": "Profit factor",
        "history.drawdown": "Drawdown réalisé maximal",
        "history.pnl_scope": (
            "Totaux de simulation issus du journal append-only, par période et devise. "
            "Ils ne constituent pas une courbe d’equity broker."
        ),
        "history.journal_unavailable": (
            "Journal détaillé non projeté dans le runtime V2. Aucun trade historique n’est inventé."
        ),
        "history.statistics_unavailable": (
            "Statistiques indisponibles tant que les trades clôturés qualifiés "
            "ne sont pas projetés."
        ),
        "history.ai_unavailable": (
            "Aucune proposition IA attestée. Aucun paramètre ne peut être appliqué automatiquement."
        ),
        "optimization.status.insufficient": (
            "INSUFFICIENT_EVIDENCE · {count} clôture(s) simulée(s) attestée(s). "
            "Aucune proposition n’est générée tant que le dataset et le replay ne sont "
            "pas qualifiés."
        ),
        "optimization.safety": (
            "Diagnostic local uniquement · aucune donnée envoyée à une IA externe · "
            "aucun paramètre modifiable depuis cette vue."
        ),
        "optimization.scope_summary": "Périmètre : {scope} · évaluation {timestamp}",
        "optimization.evidence": "Preuve / contrôle",
        "optimization.value": "Valeur",
        "optimization.scope": "Périmètre",
        "optimization.closed_trades": "Trades clôturés attestés",
        "optimization.currencies": "Devises séparées",
        "optimization.dataset_version": "Version du dataset",
        "optimization.external_ai": "Envoi IA externe",
        "optimization.not_authorized": "NON AUTORISÉ",
        "optimization.proposals": "Propositions consultatives",
        "optimization.blocker": "Blocage",
        "optimization.reason.NO_ATTESTED_CLOSED_TRADES": "Aucun trade clôturé attesté",
        "optimization.reason.SAMPLE_SIZE_EXPLORATORY": "Effectif inférieur à 30 — exploratoire",
        "optimization.reason.MULTI_CURRENCY_REQUIRES_SEPARATE_SCOPES": (
            "Plusieurs devises : analyses séparées requises"
        ),
        "optimization.reason.DATASET_NOT_VERSIONED": "Dataset non versionné",
        "optimization.reason.STRATEGY_VERSION_UNAVAILABLE": "Version de stratégie absente",
        "optimization.reason.PARAMETER_VERSION_UNAVAILABLE": "Version des paramètres absente",
        "optimization.reason.OUT_OF_SAMPLE_REPLAY_NOT_RUN": "Replay hors échantillon non exécuté",
        "optimization.reason.EXTERNAL_AI_NOT_AUTHORIZED": "Transmission IA externe non autorisée",
        "macro.ai_safety": (
            "Sources, fraîcheur, consentement et coût doivent être attestés avant tout appel IA."
        ),
        "macro.news_unavailable": "Aucun fournisseur d’actualités attesté n’est configuré.",
        "macro.calendar_unavailable": (
            "Calendrier indisponible : configurez TRADING_ECONOMICS_API_KEY puis validez "
            "explicitement le test potentiellement facturé dans les paramètres. Aucun "
            "événement n’est inventé."
        ),
        "macro.context_unavailable": "Contexte global INCONNU — aucune donnée inventée.",
        "macro.ai_unavailable": (
            "Aucun snapshot IA. Aucun appel externe n’est lancé depuis cette page."
        ),
        "macro.ai_model": "Modèle OpenAI",
        "macro.ai_tokens": "Sortie maximale",
        "macro.ai_consent": "J’autorise cet appel OpenAI unique potentiellement facturé.",
        "macro.ai_consent_detail": (
            "Jusqu’à 5 articles sélectionnés seront transmis avec leurs extraits, sources "
            "et dates ; aucun compte, ticket, ordre ou position IG."
        ),
        "macro.ai_run": "Lancer l’analyse IA consultative",
        "macro.ai_run_tooltip": (
            "Appel OpenAI unique après consentement. Le résultat ne modifie aucun paramètre "
            "et ne crée aucun ordre."
        ),
        "macro.ai_payload_preview": (
            "Aperçu avant consentement : {count} source(s), environ {input_tokens} tokens "
            "d’entrée, maximum {tokens} tokens de sortie, coût OpenAI estimé ${cost:.6f} "
            "et jusqu’à {extract_credits} crédit(s) Tavily Extract. Aucune donnée IG sensible."
        ),
        "macro.ai_evidence_used": "Extraits effectivement utilisés par la dernière analyse",
        "macro.ai_evidence_selected": "Extraits présélectionnés pour la prochaine analyse",
        "macro.ai_open_source": "Ouvrir la source sélectionnée",
        "macro.ai_excerpt": "Extrait utilisé",
        "macro.ai_excerpt_unavailable": "Contenu indisponible — métadonnées uniquement",
        "macro.ai_result_not_run": (
            "Aucune analyse IA n’a encore été lancée pour cette sélection. Le résultat "
            "apparaîtra ici après consentement explicite."
        ),
        "macro.ai_source_breakdown_empty": "Aucune source n’est encore prête pour l’IA.",
        "macro.ai_source_breakdown": (
            "Sources candidates pour le prochain appel : {total} titre(s) maximum — "
            "Tavily {tavily}, sources officielles {official}, GDELT {gdelt}."
        ),
        "macro.ai_outdated_for_collection": (
            "Cette analyse précède la dernière collecte : relancez-la explicitement pour "
            "inclure les nouvelles données Tavily/GDELT."
        ),
        "macro.ai_key_missing": (
            "OPENAI_API_KEY absente. Configurez la clé dans "
            "Paramètres > API & fournisseurs de données."
        ),
        "macro.ai_news_required": (
            "Rafraîchissez d’abord les sources officielles éligibles pour fournir des preuves."
        ),
        "macro.ai_ready_to_run": (
            "Analyse prête. Vérifiez l’aperçu, choisissez le modèle et cochez le consentement."
        ),
        "macro.ai_running": "Analyse OpenAI consultative en cours…",
        "macro.ai_ready": "Résultat consultatif · {model} · {timestamp}",
        "macro.ai_result": (
            "Synthèse : {summary}\n\nBiais : {bias}\nRisque événementiel : {risk}\n"
            "Confiance interne non calibrée : {confidence}\nDrapeaux : {flags}\n"
            "Preuves citées : {sources}\nValide jusqu’à : {validity}\n\n"
            "Aucun paramètre ni ordre n’a été créé ou modifié."
        ),
        "macro.ai_provider_official": "Source officielle",
        "macro.ai_source_citation": "• {provider} — {headline} ({source})",
        "macro.ai_busy": "Une collecte ou analyse Macro/IA est déjà en cours.",
        "macro.ai_invalid_request": "Modèle ou limite de sortie IA invalide.",
        "macro.ai_failed": "L’analyse OpenAI a échoué sans exposer de détail sensible.",
        "macro.ai_failed_retry": (
            "La demande a échoué avant de produire un résultat exploitable. Vérifiez la "
            "connexion et la clé, puis cochez de nouveau le consentement pour réessayer. "
            "Aucun ordre n’a été créé ou modifié."
        ),
        "macro.ai_persistence_failed": (
            "Le résultat IA est disponible, mais son archivage local a échoué."
        ),
        "macro.ai_attempt_unavailable": (
            "Tentative IA terminée sans résultat conforme · {timestamp} · diagnostic sûr : "
            "{reasons}."
        ),
        "macro.ai_unavailable_result": (
            "Décision : WAIT\nBiais : UNKNOWN\nRisque événementiel : UNKNOWN\n"
            "Diagnostic sûr : {reasons}\n\nLa réponse du fournisseur était absente, "
            "incomplète ou non conforme au contrat. Une limite de sortie trop basse peut "
            "notamment tronquer une réponse structurée ; 1000 jetons est la valeur conseillée.\n\n"
            "Aucun paramètre ni ordre n’a été créé ou modifié."
        ),
        "macro.ai_invalid_result": "La réponse IA ne respecte pas le contrat attendu.",
        "macro.news_refresh": "Actualiser l’analyse marché",
        "macro.news_refresh_tooltip": (
            "Collecte bornée RSS Fed/BCE, GDELT et Tavily Basic si configuré. "
            "Le quota est vérifié."
        ),
        "macro.news_refreshing": "Actualisation des métadonnées marché en cours…",
        "macro.news_ready": (
            "{count} actualité(s) issue(s) de {providers} fournisseur(s) · collecte "
            "{timestamp}. Aucun sentiment de marché ni signal d’ordre n’est déduit."
        ),
        "macro.news_failed": "Couverture actualités indisponible : {reasons}",
        "macro.intelligence.events": "Événements normalisés et dédupliqués",
        "macro.intelligence.sources": "Métadonnées sources collectées",
        "macro.intelligence.tavily_highlights": "Ce que Tavily vient d’ajouter",
        "macro.intelligence.tavily_highlights_count": (
            "Ce que Tavily vient d’ajouter — {count} résultat(s) récent(s)"
        ),
        "macro.intelligence.no_tavily_item": (
            "Aucun résultat Tavily dans cette collecte. Vérifiez l’activation et actualisez."
        ),
        "macro.intelligence.time_unknown": "heure non fournie",
        "macro.intelligence.show_raw": "Afficher les métadonnées techniques",
        "macro.intelligence.hide_raw": "Masquer les métadonnées techniques",
        "macro.intelligence.not_collected": "Aucune collecte effectuée.",
        "macro.intelligence.contribution": (
            "Apport visible — Tavily : {tavily} actualité(s) · sources officielles : "
            "{official} · GDELT : {gdelt}. Les titres sont des preuves à examiner, pas une "
            "recommandation de trading."
        ),
        "macro.intelligence.gdelt_limited": "GDELT · LIMITÉ TEMPORAIREMENT (HTTP 429)",
        "macro.intelligence.gdelt_network": "GDELT · INJOIGNABLE (RÉSEAU)",
        "macro.intelligence.gdelt_http_error": "GDELT · ERREUR DU SERVICE HTTP",
        "macro.intelligence.gdelt_empty": "GDELT · AUCUN RÉSULTAT RÉCENT",
        "macro.intelligence.gdelt_disabled": "GDELT · DÉSACTIVÉ",
        "macro.intelligence.tavily_empty": "Tavily · AUCUN RÉSULTAT RÉCENT",
        "macro.intelligence.tavily_network": "Tavily · INJOIGNABLE (RÉSEAU)",
        "macro.intelligence.tavily_quota": "Tavily · QUOTA ÉPUISÉ",
        "macro.intelligence.tavily_http_error": "Tavily · ERREUR DU SERVICE HTTP",
        "macro.intelligence.tavily_provider_error": "Tavily · RÉPONSE INEXPLOITABLE",
        "macro.intelligence.tavily_disabled": "Tavily · NON CONFIGURÉ",
        "macro.intelligence.verification": "Vérification",
        "macro.intelligence.quota": (
            "Tavily {used}/{limit} · aujourd’hui {today} · reste {remaining}"
        ),
        "macro.intelligence.freshness": "Fraîcheur · {status}",
        "macro.calendar_explanation": (
            "Tavily et GDELT recherchent des actualités publiées ; ils ne fournissent pas un "
            "calendrier économique futur structuré. Aucun événement futur n’est donc déduit de "
            "leurs titres. Un connecteur de calendrier dédié reste nécessaire."
        ),
        "macro.context_observed": (
            "Couverture factuelle observée. Aucun biais haussier ou baissier n’est inventé."
        ),
        "macro.context_coverage": (
            "{total} titre(s) répartis sur {providers} fournisseur(s) · fraîcheur {freshness}. "
            "La table indique les thèmes couverts ; la direction de marché reste INCONNUE "
            "jusqu’à une analyse explicitement lancée."
        ),
        "macro.context.category": "Thème observé",
        "macro.context.items": "Nombre de titres",
        "macro.news.published": "Publié à",
        "macro.news.source": "Source",
        "macro.news.headline": "Titre",
        "macro.news.category": "Catégorie",
        "macro.news.importance": "Importance",
        "catalogue.busy": "Une recherche catalogue est déjà en cours.",
        "catalogue.not_connected": "Connectez d’abord le compte DEMO en lecture seule.",
        "catalogue.invalid_query": "La recherche doit contenir entre 3 et 100 caractères.",
        "catalogue.context_changed": "Résultat ignoré : le contexte de compte a changé.",
        "catalogue.cache_invalid": "L’inventaire local IG est illisible et a été ignoré.",
        "stream.start": "Suivre la sélection en direct",
        "stream.stop": "Arrêter le direct",
        "stream.not_connected": "Connectez d’abord un compte IG en lecture seule.",
        "stream.chart_group_degraded": (
            "IG refuse le flux graphique groupé ; nouvelle tentative marché par marché."
        ),
        "stream.chart_market_unavailable": (
            "Certains graphiques de référence ne sont pas autorisés sur ce compte IG ; "
            "les cotations des produits restent actives."
        ),
        "stream.price_group_degraded": (
            "IG refuse ce lot de cotations ; isolation automatique marché par marché."
        ),
        "stream.price_market_unavailable": (
            "Un produit visible n’est pas disponible en flux sur ce compte IG ; "
            "les autres cotations restent actives."
        ),
        "stream.product_unknown": "Sélection absente du catalogue courant.",
        "stream.unavailable": "Le compte IG ne fournit pas de point d’accès temps réel.",
        "stream.state.disconnected": "Flux direct arrêté — sélectionnez un produit.",
        "stream.state.connecting": "Connexion au flux pour {epic}…",
        "stream.state.connected": "Flux connecté pour {epic}; abonnement en cours…",
        "stream.state.subscribing": "Abonnement limité à {epic}…",
        "stream.state.subscribed_waiting_first_tick": (
            "{epic} abonné — attente de la première cotation."
        ),
        "stream.state.live": "{epic} en direct — Bid/Offer/Variation mis à jour par IG.",
        "stream.state.reconnecting": "Reconnexion du flux {epic}…",
        "stream.state.stale": "Flux {epic} interrompu ou périmé.",
        "stream.state.failed": "Flux {epic} indisponible.",
        "stream.state.unknown": "État du flux {epic} : non déterminé.",
        "stream.coverage": (
            "Flux IG : {subscribed}/39 cotation(s), dont {priority} marché(s) prioritaire(s) "
            "permanent(s), + compte · {total} ligne(s) filtrée(s) · état {state}."
        ),
        "stream.short.disconnected": "déconnecté",
        "stream.short.connecting": "connexion",
        "stream.short.connected": "connecté",
        "stream.short.subscribing": "abonnement",
        "stream.short.subscribed_waiting_first_tick": "attente de cotation",
        "stream.short.live": "temps réel",
        "stream.short.reconnecting": "reconnexion",
        "stream.short.stale": "périmé",
        "stream.short.failed": "indisponible",
        "catalogue.column.name": "Marché",
        "catalogue.column.live": "●",
        "catalogue.live.header_tooltip": "Fraîcheur de la cotation",
        "catalogue.live.updated": "Cotation mise à jour par le flux IG courant.",
        "catalogue.live.not_updated": "Cotation non mise à jour par le flux IG courant.",
        "catalogue.column.epic": "EPIC",
        "catalogue.column.type": "Produit",
        "catalogue.column.direction": "Direction",
        "catalogue.column.asset": "Classe",
        "catalogue.column.bid": "Bid",
        "catalogue.column.offer": "Offer",
        "catalogue.column.change": "Variation",
        "catalogue.column.source": "Source",
        "catalogue.column.status": "Statut",
        "macro.title": "Contexte marché",
        "macro.empty": "Contexte indisponible — aucune donnée inventée",
        "macro.ribbon.news_ready": (
            "Veille disponible · {news} actualité(s) / {providers} fournisseur(s) · "
            "analyse IA non disponible"
        ),
        "macro.ribbon.news_tooltip": (
            "Dernière collecte attestée : {collected}\n"
            "État IA : {reasons}\n"
            "Contexte consultatif uniquement ; aucune exécution n’est déclenchée."
        ),
        "macro.ribbon.ai_ready": (
            "Biais {bias} · risque {risk} · confiance {confidence} · "
            "{news} actualité(s) / {providers} fournisseur(s)"
        ),
        "macro.ribbon.ai_tooltip": (
            "Synthèse : {summary}\nValide jusqu’à : {validity}\nDrapeaux : {flags}\n"
            "Contexte consultatif uniquement ; aucune exécution n’est déclenchée."
        ),
        "page.empty.title": "Fondation GUI V2",
        "page.empty.body": "Cette page attend une projection attestée du runtime unique.",
        "page.empty.no_network": "L’ouverture de cette page ne déclenche aucun appel réseau.",
        "settings.language": "Langue",
        "settings.theme": "Thème",
        "tab.overview": "Vue d’ensemble",
        "tab.performance": "Performance",
        "tab.ai_improvement": "IA / Amélioration",
        "tab.opportunities": "Opportunités",
        "tab.long": "Long / Haussier",
        "tab.short": "Short / Baissier",
        "tab.watch": "À surveiller",
        "tab.catalog": "Catalogue IG",
        "tab.chart": "Graphique",
        "tab.technical": "Analyse technique",
        "tab.ai_analysis": "Analyse IA",
        "tab.trade_plan": "Plan de trade",
        "tab.market_history": "Historique du marché",
        "tab.open_positions": "Positions ouvertes",
        "tab.pending": "En attente",
        "tab.order_history": "Historique des ordres",
        "tab.paper": "Simulation",
        "tab.alerts": "Alertes",
        "tab.trade_journal": "Journal des trades",
        "tab.pnl": "PnL",
        "tab.statistics": "Statistiques",
        "tab.ai_optimization": "Optimisation IA",
        "tab.news": "Actualités",
        "tab.calendar": "Calendrier",
        "tab.global_context": "Contexte global",
        "tab.ai_snapshots": "Analyses IA",
        "tab.service_health": "Santé des services",
        "tab.flows_quotas": "Flux / quotas",
        "tab.incidents": "Incidents",
        "tab.logs": "Journaux",
        "tab.connections": "API & fournisseurs de données",
        "tab.markets": "Marchés",
        "tab.strategies": "Stratégies",
        "tab.risk": "Risques",
        "tab.ai": "IA",
        "tab.notifications": "Notifications",
        "tab.interface": "Interface",
        "tab.advanced": "Avancé",
    },
    "en_US": {
        "app.title": "TradingIG — Analysis and Simulation",
        "nav.dashboard": "Dashboard",
        "nav.scanner": "Markets / Scanner",
        "nav.watchlist": "Watchlist",
        "nav.positions": "Positions & Orders",
        "nav.history": "History / Analytics",
        "nav.macro": "Macro / AI",
        "nav.diagnostics": "Diagnostics",
        "nav.settings": "Settings",
        "nav.collapse": "Collapse navigation",
        "nav.expand": "Expand navigation",
        "header.account": "Account",
        "header.no_account": "No account",
        "header.environment": "Environment",
        "header.execution": "Mode",
        "header.data": "Data",
        "header.ai": "AI",
        "header.connect": "Connect",
        "header.connecting": "Connecting…",
        "header.connected": "Connected ✓",
        "header.disconnect_action": "Disconnect",
        "header.connect_help": "Open a read-only IG session.",
        "header.connected_help": "IG session connected. Click to disconnect.",
        "header.read_only_safety": "{environment} · SIMULATION · no IG order",
        "header.account_family_cfd": "CFD",
        "header.account_family_options": "BARRIERS & OPTIONS",
        "header.account_family_spreadbet": "SPREAD BET",
        "header.account_family_shares": "SHARES",
        "header.account_family_unknown": "IG ACCOUNT",
        "header.account_connect_first": "No account — connect DEMO or LIVE",
        "header.account_selector_help": (
            "Accounts from the connected IG environment. Disconnect the active session before "
            "switching between DEMO and LIVE."
        ),
        "header.account_metrics_unavailable": (
            "IG equity: N/A · Balance: N/A · Available: N/A · PnL: N/A"
        ),
        "header.account_metrics": (
            "IG equity: {equity} · Balance: {balance} · Available: {available} · PnL: {pnl}"
        ),
        "header.account_metrics_tooltip": "REST/stream account data received at {timestamp}",
        "header.metric.equity": "IG equity",
        "header.metric.balance": "Balance",
        "header.metric.available": "Available",
        "header.metric.pnl": "IG PnL",
        "status.analysis": "ANALYSIS",
        "status.paper": "SIMULATION",
        "status.disconnected": "Disconnected",
        "status.not_configured": "Not configured",
        "status.ai.not_configured": "not configured",
        "status.ai.configured": "configured · manual launch",
        "status.ai.running": "analysis running",
        "status.ai.ready": "latest analysis available",
        "status.ai.stale": "latest analysis stale",
        "status.unavailable": "Unavailable",
        "status.unknown": "Unknown",
        "connection.busy": "A connection operation is already running.",
        "connection.already_connected": "An IG account is already connected.",
        "connection.profile_missing.demo": "Configure the IG DEMO profile first.",
        "connection.profile_missing.live": "Configure the IG LIVE profile first.",
        "connection.store_unavailable": "The system credential store is unavailable.",
        "connection.credentials_missing.demo": "DEMO credentials are missing from the store.",
        "connection.credentials_missing.live": "LIVE credentials are missing from the store.",
        "connection.not_connected": "No IG account is connected.",
        "connection.account_unknown": "This account is not part of the active session.",
        "connection.invalid_result": "The connection returned an invalid result.",
        "connection.session_token_invalid": (
            "IG rejected two consecutive session tokens. Wait about one minute, then reconnect. "
            "The credentials and API key were accepted."
        ),
        "connection.config_save_failed": (
            "The account is connected, but the profile could not be saved."
        ),
        "connection.closing": "Closing after the connection operation finishes…",
        "dashboard.scope.unavailable": "Simulation session unavailable — no data invented",
        "dashboard.scope.paper": "SIMULATION · {account} · projection {timestamp}",
        "dashboard.kpi.equity": "Equity",
        "dashboard.kpi.balance": "IG account balance",
        "dashboard.kpi.available": "Available funds",
        "dashboard.kpi.account_pnl": "Current IG PnL",
        "dashboard.kpi.margin": "IG deposit / margin",
        "dashboard.kpi.day_pnl": "Realized PnL day",
        "dashboard.kpi.week_pnl": "Realized PnL week",
        "dashboard.kpi.month_pnl": "Realized PnL month",
        "dashboard.kpi.positions": "Open simulated positions",
        "dashboard.kpi.win_rate": "Win rate",
        "dashboard.kpi.profit_factor": "Profit factor",
        "dashboard.kpi.drawdown": "Drawdown",
        "dashboard.positions.title": "Open simulated positions — read-only",
        "dashboard.positions.empty": "No open simulated position in this session.",
        "dashboard.performance.unavailable": "Simulation history unavailable.",
        "dashboard.performance.no_equity_history": (
            "No equity curve is shown: no attested historical snapshot exists. "
            "Totals below, when present, are realized PnL only."
        ),
        "dashboard.performance.period.day": "Day",
        "dashboard.performance.period.week": "Week",
        "dashboard.performance.period.month": "Month",
        "dashboard.performance.period.year": "Year",
        "dashboard.performance.mode.currency": "Realized amount",
        "dashboard.performance.mode.percent": "% of opening capital",
        "dashboard.performance.no_realized_pnl": (
            "No attested realized PnL for this period and currency."
        ),
        "dashboard.performance.percent_unavailable": (
            "N/A: no timestamped opening capital supports an attested percentage."
        ),
        "dashboard.performance.realized_scope": (
            "Realized simulated PnL · {currency} · {count} attested closure(s)."
        ),
        "dashboard.ai.unavailable": (
            "No attested AI proposal. Nothing is generated or applied automatically."
        ),
        "dashboard.position.product": "Product",
        "dashboard.position.direction": "Direction",
        "dashboard.position.quantity": "Quantity",
        "dashboard.position.entry": "Entry",
        "dashboard.position.mark": "Mark price",
        "dashboard.position.pnl": "Estimated net PnL",
        "dashboard.position.stop": "Confirmed stop",
        "dashboard.position.status": "State",
        "catalogue.search": "Add from IG",
        "catalogue.follow": "Add to watchlist",
        "catalogue.query_placeholder": "Filter the catalogue as you type…",
        "catalogue.empty": "No local inventory is available. Navigation does not call IG.",
        "catalogue.inventory": (
            "Catalogue: {count} product(s) · {visible} visible · local inventory {timestamp}. "
            "Typing filters locally without calling IG."
        ),
        "catalogue.results": (
            "{visible}/{count} product(s) visible · last IG addition “{query}” · "
            "snapshot {timestamp}."
        ),
        "catalogue.analysis_unavailable": (
            "Analysis unavailable: no attested closed candle in the V2 runtime."
        ),
        "scanner.status.unavailable": "Scanner unavailable — no invented data.",
        "scanner.status.summary": (
            "{visible}/{configured} market(s) shown · state {state} · projection {timestamp}. "
            "Scores remain UNKNOWN until attested session candles exist."
        ),
        "scanner.column.market": "Reference market",
        "scanner.column.asset": "Asset class",
        "scanner.column.last": "Last",
        "scanner.column.change": "Change",
        "scanner.column.freshness": "Source / age",
        "scanner.column.technical": "Technical",
        "scanner.column.context": "Context",
        "scanner.context.unknown": "UNKNOWN",
        "scanner.context.catalyst": "CATALYST",
        "scanner.context.aligned": "ALIGNED",
        "scanner.context.caution": "CAUTION",
        "scanner.context.unfavorable": "UNFAVORABLE",
        "scanner.context.no_evidence": (
            "No attested macro/AI context applies to this product."
        ),
        "scanner.context.veto_yes": "yes",
        "scanner.context.veto_no": "no",
        "scanner.context.tooltip": (
            "Advisory context only — neither a recommendation nor a probability.\n"
            "Components:\n{components}\nSafety veto: {veto}\n"
            "Reasons: {reasons}\nProvenance: {provenance}"
        ),
        "scanner.column.direction": "Direction",
        "scanner.column.decision": "Decision",
        "scanner.column.reason": "Reason",
        "scanner.column.evaluated": "Evaluated at",
        "scanner.direction.unknown": "UNKNOWN",
        "scanner.direction.bullish": "BULLISH",
        "scanner.direction.bearish": "BEARISH",
        "scanner.direction.neutral": "NEUTRAL",
        "scanner.decision.unavailable": "UNAVAILABLE",
        "scanner.decision.candidate": "OPPORTUNITY",
        "scanner.decision.watch": "WATCH",
        "scanner.decision.no_trade": "NO_TRADE",
        "scanner.reason.session_ohlc_warming_up": ("Session candles: {observed}/{required}"),
        "scanner.reason.analysis_pending": "Analysis pending ({observed} candles)",
        "scanner.reason.no_confirmed_breakout": "No confirmed breakout",
        "watchlist.analysis_pending": (
            "Advisory analysis is waiting for enough attested data. "
            "No ticket or order is created from this view."
        ),
        "watchlist.no_market": "No reference market is selected.",
        "watchlist.no_product": "No followed product",
        "watchlist.remove_product": "Remove from watchlist",
        "watchlist.technical.summary": (
            "{market} · Direction {direction} · Decision {decision} · "
            "Technical {technical} · Context {context}\n"
            "Observed closed candles: {observed}/{required} · Evaluated: {evaluated}\n"
            "Reasons: {reasons}. Scores are explainable rankings, not probabilities."
        ),
        "watchlist.technical.product_fallback": (
            "Fallback source: M1 candles built from the exact product PRICE quotes; they are "
            "not presented as the underlying chart."
        ),
        "watchlist.signal.strategy": "Strategy",
        "watchlist.signal.product": "Product",
        "watchlist.signal.direction": "Signal",
        "watchlist.signal.state": "Data",
        "watchlist.signal.entry": "Entry",
        "watchlist.signal.invalidation": "Inv.",
        "watchlist.signal.target": "Tgt.",
        "watchlist.signal.valid_until": "Expires",
        "watchlist.technical.no_signal": (
            "No attested strategy signal is available for this market."
        ),
        "watchlist.technical.detail": (
            "Signal: {signal_id} · Confidence: {confidence} · Quality: {quality}\n"
            "Generated: {generated} · Valid until: {valid_until}\n"
            "Reasons: {reasons}\nProvenance: {provenance}\n"
            "Attested features:\n{features}"
        ),
        "watchlist.plan.long": "Bullish / LONG scenario",
        "watchlist.plan.short": "Bearish / SHORT scenario",
        "watchlist.plan.no_trade": "NO_TRADE / Blockers",
        "watchlist.plan.unavailable": (
            "{direction} — no attested READY signal. No proposal is inferred."
        ),
        "watchlist.plan.scenario": (
            "{direction} · {strategy}\nEvidence product: {product}\n"
            "Entry: {entry} · Invalidation: {invalidation} · Target: {target}\n"
            "Valid until: {validity}\n"
            "Market direction only; no IG order side is inferred."
        ),
        "watchlist.plan.blockers": (
            "Scanner decision: {decision}\nBlockers: {blockers}\n"
            "No ticket or order is generated from this summary."
        ),
        "chart.overlay.entry_min": "Entry−",
        "chart.overlay.entry_max": "Entry+",
        "chart.overlay.invalidation": "Inv.",
        "chart.overlay.target": "Tgt.",
        "chart.overlay.fast_ema": "EMA F",
        "chart.overlay.slow_ema": "EMA S",
        "chart.overlay.support": "Sup.",
        "chart.overlay.resistance": "Res.",
        "watchlist.overlay.title": "Displayed signal:",
        "watchlist.overlay.signal_option": "{strategy} · {direction} · {state}",
        "watchlist.overlay.signal_selector_tooltip": (
            "Choose the strategy projected on the chart. The matching Technical analysis "
            "row is selected; other ready indicators are not overlaid on this signal."
        ),
        "watchlist.overlay.entry": "Entry zone",
        "watchlist.overlay.invalidation": "Invalidation",
        "watchlist.overlay.target": "Target",
        "watchlist.overlay.ema": "EMA",
        "watchlist.overlay.rsi": "RSI",
        "watchlist.overlay.structure": "Support / Resistance",
        "watchlist.overlay.indicator_panel": "Lower panel:",
        "watchlist.overlay.indicator_panel_tooltip": (
            "Only one indicator with its own scale is displayed below price."
        ),
        "watchlist.panel.none": "None",
        "chart.panel.rsi.oversold": "Oversold",
        "chart.panel.rsi.overbought": "Overbought",
        "chart.panel.macd.line": "MACD",
        "chart.panel.macd.signal": "Signal",
        "chart.panel.macd.histogram": "Histogram",
        "watchlist.overlay.availability_tooltip": (
            "A checkbox is active only when the selected signal produces that datum."
        ),
        "watchlist.indicators.unavailable": (
            "Indicators: select an attested technical signal."
        ),
        "watchlist.indicators.snapshot": (
            "M1 snapshot for {strategy} · ATR: {atr} · RSI: {rsi}. "
            "Historical curves are not invented."
        ),
        "watchlist.indicators.snapshot_detailed": (
            "Displayed signal {strategy} · data usable by this signal: {values}. Other "
            "market-ready indicators remain visible in Technical analysis but are not "
            "applied to this signal."
        ),
        "watchlist.indicators.none_for_signal": "no numeric indicator available",
        "watchlist.indicators.atr": "ATR",
        "watchlist.indicators.rsi": "RSI",
        "watchlist.indicators.fast_ema": "Fast EMA",
        "watchlist.indicators.slow_ema": "Slow EMA",
        "watchlist.indicators.support": "Support",
        "watchlist.indicators.resistance": "Resistance",
        "watchlist.indicators.heading": (
            "Market-ready indicators — all active strategies"
        ),
        "watchlist.indicator.column.name": "Indicator",
        "watchlist.indicator.column.value": "Value",
        "watchlist.indicator.column.params": "Params",
        "watchlist.indicator.column.state": "State",
        "watchlist.indicator.column.candles": "Candles",
        "watchlist.indicator.column.source": "Source",
        "watchlist.indicator.state.ready": "READY",
        "watchlist.indicator.state.warming_up": "WARMING",
        "watchlist.indicator.state.invalid": "INVALID",
        "watchlist.indicator.name.ema": "EMA",
        "watchlist.indicator.name.atr": "ATR",
        "watchlist.indicator.name.rsi": "RSI",
        "watchlist.indicator.name.recent_levels": "Recent levels",
        "watchlist.indicator.name.volume_ratio": "Volume ratio",
        "watchlist.indicator.component.support": "Support",
        "watchlist.indicator.component.resistance": "Resistance",
        "watchlist.indicator.tooltip": (
            "Reasons: {reasons}\nProvenance:\n{provenance}"
        ),
        "watchlist.ai.unavailable": (
            "UNKNOWN — no specific attested AI analysis is associated with {market} ({epic}) "
            "in this session. Macro / AI allows a manual advisory call with consent; changing "
            "tabs never triggers an OpenAI call."
        ),
        "watchlist.ai.unavailable_reasons": (
            "Reasons: {reasons}. Verify sources, then manually run an advisory analysis from "
            "Macro / AI."
        ),
        "watchlist.ai.scope_global": "global market context",
        "watchlist.ai.scope_mismatch": (
            "{market} — the latest AI analysis is out of scope (scope: {scope})."
        ),
        "watchlist.ai.scope_mismatch_detail": (
            "No instrument-specific bias is inferred from an analysis of another instrument. "
            "Open Macro / AI to inspect or rerun the analysis."
        ),
        "watchlist.ai.stale": (
            "{market} — advisory analysis is stale ({scope}). Generated: {generated} · valid "
            "until: {valid_until}. Rerun the analysis before interpreting it."
        ),
        "watchlist.ai.summary": (
            "{market} — advisory analysis ({scope})\n"
            "Bias: {bias} · event risk: {risk} · uncalibrated internal index: {confidence}\n"
            "Generated: {generated} · valid until: {valid_until}\n"
            "Summary: {summary}\nFlags: {flags}\n"
            "A global scope describes shared context, not an instrument-specific bias. This "
            "analysis is neither an order nor a probability of success."
        ),
        "watchlist.ai.sources": "Sources used ({count}):\n{sources}",
        "watchlist.ai.open_macro": "Open Macro / AI",
        "watchlist.history.session_only": (
            "History is strictly limited to this session · EPIC {epic}\n"
            "Observed M1 candles: {candles} · First: {first} · Last: {last}\n"
            "No IG history, backtest or trade is invented or loaded automatically."
        ),
        "positions.safety": (
            "Read-only · local simulated positions remain separate from IG broker data · "
            "no modify or close action is available."
        ),
        "positions.broker_unavailable": (
            "Broker position/order data is not loaded in the V2 runtime. No data is simulated."
        ),
        "positions.paper_empty": "No open simulated position in this session.",
        "positions.pending_unavailable": (
            "No pending broker order is loaded in V2. No data is simulated."
        ),
        "positions.order_history_unavailable": (
            "Broker order history is not loaded. The local simulation journal remains available "
            "under History / Analytics."
        ),
        "positions.alerts_empty": (
            "No local alert was observed in this session. The persistent inbox and external "
            "notifications are not enabled yet."
        ),
        "paper.save": "Save simulation session",
        "paper.restore": "Restore latest session",
        "paper.local_only": "Local storage only — nothing is sent to IG.",
        "paper.save_empty": "There is no simulation state to save.",
        "paper.save_succeeded": "Simulation session saved locally.",
        "paper.save_failed": "Simulation save refused: {detail}",
        "paper.restore_missing": "There is no local simulation database to restore.",
        "paper.restore_empty": "The local database contains no simulation snapshot.",
        "paper.restore_succeeded": (
            "Latest simulation session restored locally — nothing was sent to IG."
        ),
        "paper.restore_failed": "Simulation restore refused: {detail}",
        "paper.restore_title": "Restore simulation session",
        "paper.restore_question": (
            "Replace the current local simulation session with the latest snapshot?"
        ),
        "paper.stop": "Tighten simulated stop",
        "paper.stop_title": "Local simulated stop",
        "paper.stop_question": "New stop level:",
        "paper.stop_invalid": "Invalid stop level.",
        "paper.stop_succeeded": "Local simulated stop updated and attested.",
        "paper.stop_failed": "Simulated stop update refused: {detail}",
        "paper.close": "Close simulated position",
        "paper.close_title": "Close simulated position",
        "paper.close_question": (
            "Close local position {position_id} at the latest executable price?"
        ),
        "paper.close_succeeded": "Simulated position closed locally.",
        "paper.close_failed": "Simulated close refused: {detail}",
        "paper.open_title": "Confirm local simulated opening",
        "paper.open_question": (
            "Open this position in the local simulation session only?\n\n"
            "Exact product: {product}\nCanonical market: {underlying}\n"
            "Order side: {direction}\nQuantity: {quantity}\nSimulated entry: {entry}\n"
            "Stop: {stop}\nTarget: {target}\nKO: {knockout}\n"
            "Estimated loss: {loss} {currency}\nEstimated costs: {costs} {currency}\n"
            "Price source: {source}\nTimestamp: {timestamp}\n\n"
            "This action sends no order to IG."
        ),
        "paper.open_succeeded": "Position opened in the local simulation session.",
        "paper.open_invalid": "Invalid simulation submission.",
        "paper.open_stale": "Simulated opening refused: the quote has expired.",
        "paper.open_expired": "Simulated opening refused: the draft has expired.",
        "paper.open_failed": "Simulated opening refused: {detail}",
        "paper.ticket.preparation_safety": (
            "Local simulation preparation. The exact IG product, its canonical binding and a fresh "
            "live quote are required. Local opening requires RiskEngine evaluation and explicit "
            "confirmation; no order is sent to IG."
        ),
        "paper.ticket.select_product": (
            "Double-click an exact product in the IG Catalogue to prepare its checks."
        ),
        "paper.ticket.ready": (
            "READY FOR PREPARATION — identity, binding and quote are attested. Explicit local "
            "simulation confirmation remains required."
        ),
        "paper.ticket.prepare_draft": "Prepare simulation draft",
        "paper.ticket.back_to_evidence": "Back to checks",
        "paper.ticket.blocked": "{status} — simulation preparation is blocked.",
        "paper.ticket.field": "Control",
        "paper.ticket.value": "Attested value",
        "paper.ticket.product": "Product",
        "paper.ticket.product_epic": "Exact product EPIC",
        "paper.ticket.product_type": "Product type",
        "paper.ticket.underlying": "Canonical market",
        "paper.ticket.reference_epic": "Reference EPIC",
        "paper.ticket.binding_provenance": "Binding provenance",
        "paper.ticket.metadata_source": "Metadata source",
        "paper.ticket.currency": "Currency",
        "paper.ticket.deal_constraints": "Product constraints",
        "paper.ticket.bid_offer": "Bid / Offer",
        "paper.ticket.market_status": "Market status",
        "paper.ticket.quote_source": "Source / received",
        "paper.ticket.blocker": "Blocker",
        "paper.ticket.reason.EXACT_PRODUCT_BINDING_REQUIRED": (
            "Exact product-to-market binding missing; no name or EPIC inference"
        ),
        "paper.ticket.reason.PRODUCT_TYPE_UNKNOWN": "Unknown product type",
        "paper.ticket.reason.PRODUCT_CURRENCY_UNAVAILABLE": "Product currency unavailable",
        "paper.ticket.reason.BID_OFFER_UNAVAILABLE": "Bid/Offer unavailable",
        "paper.ticket.reason.BID_OFFER_INVALID": "Invalid Bid/Offer",
        "paper.ticket.reason.MARKET_NOT_CONFIRMED_TRADEABLE": (
            "Market not confirmed TRADEABLE"
        ),
        "paper.ticket.reason.LIVE_QUOTE_REQUIRED": "Lightstreamer quote required",
        "paper.ticket.reason.LIVE_QUOTE_STALE": "Live quote is stale",
        "paper.ticket.reason.BROKER_DELAYED": "Broker quote is delayed",
        "diagnostics.service": "Service",
        "diagnostics.state": "State",
        "diagnostics.summary": "Summary",
        "diagnostics.observed": "Observed at",
        "diagnostics.reasons": "Reasons",
        "diagnostics.service.ig-rest": "IG REST",
        "diagnostics.service.ig-streaming": "IG Streaming",
        "diagnostics.service.openai": "OpenAI",
        "diagnostics.service.paper-sqlite": "SQLite / simulation",
        "diagnostics.service.official-news": "Official news",
        "diagnostics.status.ready": "READY",
        "diagnostics.status.warming_up": "WARMING UP",
        "diagnostics.status.stale": "STALE",
        "diagnostics.status.unavailable": "UNAVAILABLE",
        "diagnostics.status.not_applicable": "NOT APPLICABLE",
        "diagnostics.summary.connected": "Connected",
        "diagnostics.summary.connecting": "Connecting",
        "diagnostics.summary.disconnected": "Disconnected",
        "diagnostics.summary.live": "Live stream",
        "diagnostics.summary.not_configured": "Not configured",
        "diagnostics.summary.empty_session": "Empty local session",
        "diagnostics.summary.unsaved_changes": "Unsaved changes",
        "diagnostics.summary.snapshot_saved": "Snapshot saved",
        "diagnostics.summary.error": "Persistence error",
        "diagnostics.summary.metadata_available": "Metadata available",
        "diagnostics.summary.not_collected": "Not collected",
        "diagnostics.summary.configured": "Configured — manual action required",
        "diagnostics.summary.last_request_available": "Latest analysis available",
        "diagnostics.summary.last_request_stale": "Latest analysis stale",
        "diagnostics.summary.ready": "Ready",
        "diagnostics.summary.running": "Analysis running",
        "diagnostics.no_active_probe": (
            "This page performs no active probe. Only actually observed events are shown."
        ),
        "settings.connections_summary": (
            "Configured environment: {environment}\nRead-only mode: enabled\n"
            "LIVE/AUTO trading: disabled and cannot be enabled from GUI V2."
        ),
        "settings.markets_summary": "{bindings} exact product/market binding(s) configured.",
        "settings.strategies_summary": (
            "Opportunity threshold: {candidate}/100\nWatch threshold: {watch}/100\n"
            "Strategy changes are not exposed in this lot."
        ),
        "settings.risk_summary": (
            "Existing safeguards remain active. No risk setting is changed automatically."
        ),
        "settings.ai_summary": (
            "Advisory AI only. No external call or parameter change without explicit consent."
        ),
        "settings.notifications_summary": "Advanced notifications are not configured.",
        "settings.advanced_summary": (
            "Advanced configuration is read-only in this lot. Secrets are never displayed."
        ),
        "history.period": "Period",
        "history.period_key": "Key",
        "history.amount": "Realized PnL",
        "history.events": "Events",
        "history.journal_scope": (
            "Append-only journal for the local simulation session. Internal payloads are not "
            "exposed in this view."
        ),
        "history.journal_filter": "Filter by event, market, or correlation…",
        "history.timestamp": "Timestamp",
        "history.event_type": "Event",
        "history.instrument": "Instrument",
        "history.correlation": "Correlation",
        "history.pnl": "PnL",
        "history.pnl_status": "PnL status",
        "history.statistics_scope": (
            "Attested realized simulated closures only. Currencies are never merged; a small "
            "sample remains exploratory."
        ),
        "history.metric": "Metric",
        "history.value": "Value",
        "history.win_rate": "Win rate",
        "history.profit_factor": "Profit factor",
        "history.drawdown": "Maximum realized drawdown",
        "history.pnl_scope": (
            "Simulation totals from the append-only journal, grouped by period and currency. "
            "They are not a broker equity curve."
        ),
        "history.journal_unavailable": (
            "The detailed journal is not projected in V2. No historical trade is invented."
        ),
        "history.statistics_unavailable": (
            "Statistics remain unavailable until qualified closed trades are projected."
        ),
        "history.ai_unavailable": (
            "No attested AI proposal exists. No parameter can be applied automatically."
        ),
        "optimization.status.insufficient": (
            "INSUFFICIENT_EVIDENCE · {count} attested closed simulated trade(s). "
            "No proposal is generated until the dataset and replay are qualified."
        ),
        "optimization.safety": (
            "Local diagnostics only · no data sent to external AI · "
            "no parameter can be changed from this view."
        ),
        "optimization.scope_summary": "Scope: {scope} · assessed {timestamp}",
        "optimization.evidence": "Evidence / control",
        "optimization.value": "Value",
        "optimization.scope": "Scope",
        "optimization.closed_trades": "Attested closed trades",
        "optimization.currencies": "Separate currencies",
        "optimization.dataset_version": "Dataset version",
        "optimization.external_ai": "External AI transfer",
        "optimization.not_authorized": "NOT AUTHORIZED",
        "optimization.proposals": "Advisory proposals",
        "optimization.blocker": "Blocker",
        "optimization.reason.NO_ATTESTED_CLOSED_TRADES": "No attested closed trade",
        "optimization.reason.SAMPLE_SIZE_EXPLORATORY": "Sample below 30 — exploratory",
        "optimization.reason.MULTI_CURRENCY_REQUIRES_SEPARATE_SCOPES": (
            "Multiple currencies: separate analyses required"
        ),
        "optimization.reason.DATASET_NOT_VERSIONED": "Dataset is not versioned",
        "optimization.reason.STRATEGY_VERSION_UNAVAILABLE": "Strategy version unavailable",
        "optimization.reason.PARAMETER_VERSION_UNAVAILABLE": "Parameter version unavailable",
        "optimization.reason.OUT_OF_SAMPLE_REPLAY_NOT_RUN": "Out-of-sample replay not run",
        "optimization.reason.EXTERNAL_AI_NOT_AUTHORIZED": "External AI transfer not authorized",
        "macro.ai_safety": (
            "Sources, freshness, consent and cost must be attested before any AI call."
        ),
        "macro.news_unavailable": "No attested news provider is configured.",
        "macro.calendar_unavailable": (
            "Calendar unavailable: configure TRADING_ECONOMICS_API_KEY, then explicitly "
            "approve the potentially billed test in settings. No event is invented."
        ),
        "macro.context_unavailable": "Global context UNKNOWN — no invented data.",
        "macro.ai_unavailable": "No AI snapshot. This page makes no external call.",
        "macro.ai_model": "OpenAI model",
        "macro.ai_tokens": "Maximum output",
        "macro.ai_consent": "I authorize this single potentially billed OpenAI call.",
        "macro.ai_consent_detail": (
            "Up to 5 selected articles will be sent with excerpts, sources and dates; no IG "
            "account, ticket, order or position."
        ),
        "macro.ai_run": "Run advisory AI analysis",
        "macro.ai_run_tooltip": (
            "Single OpenAI call after consent. The result changes no parameter and creates "
            "no order."
        ),
        "macro.ai_payload_preview": (
            "Preview before consent: {count} source(s), about {input_tokens} input tokens, "
            "up to {tokens} output tokens, estimated OpenAI cost ${cost:.6f}, and up to "
            "{extract_credits} Tavily Extract credit(s). No sensitive IG data."
        ),
        "macro.ai_evidence_used": "Excerpts actually used by the latest analysis",
        "macro.ai_evidence_selected": "Excerpts selected for the next analysis",
        "macro.ai_open_source": "Open selected source",
        "macro.ai_excerpt": "Excerpt used",
        "macro.ai_excerpt_unavailable": "Content unavailable — metadata only",
        "macro.ai_result_not_run": (
            "No AI analysis has been run for this selection yet. The result will appear "
            "here after explicit consent."
        ),
        "macro.ai_source_breakdown_empty": "No source is ready for AI yet.",
        "macro.ai_source_breakdown": (
            "Candidate sources for the next call: up to {total} headline(s) — Tavily "
            "{tavily}, official sources {official}, GDELT {gdelt}."
        ),
        "macro.ai_outdated_for_collection": (
            "This analysis predates the latest collection: run it explicitly again to include "
            "the new Tavily/GDELT data."
        ),
        "macro.ai_key_missing": (
            "OPENAI_API_KEY is missing. Configure the key in Settings > API & Data Providers."
        ),
        "macro.ai_news_required": (
            "Refresh eligible official sources first so the analysis has cited evidence."
        ),
        "macro.ai_ready_to_run": (
            "Analysis ready. Review the payload, choose the model and check consent."
        ),
        "macro.ai_running": "Advisory OpenAI analysis in progress…",
        "macro.ai_ready": "Advisory result · {model} · {timestamp}",
        "macro.ai_result": (
            "Summary: {summary}\n\nBias: {bias}\nEvent risk: {risk}\n"
            "Uncalibrated internal confidence: {confidence}\nFlags: {flags}\n"
            "Cited evidence: {sources}\nValid until: {validity}\n\n"
            "No parameter or order was created or changed."
        ),
        "macro.ai_provider_official": "Official source",
        "macro.ai_source_citation": "• {provider} — {headline} ({source})",
        "macro.ai_busy": "A Macro/AI collection or analysis is already running.",
        "macro.ai_invalid_request": "Invalid AI model or output limit.",
        "macro.ai_failed": "OpenAI analysis failed without exposing sensitive details.",
        "macro.ai_failed_retry": (
            "The request failed before producing a usable result. Check the connection and "
            "key, then consent again to retry. No order was created or modified."
        ),
        "macro.ai_persistence_failed": (
            "The AI result is available, but local archival failed."
        ),
        "macro.ai_attempt_unavailable": (
            "AI attempt completed without a compliant result · {timestamp} · safe diagnostic: "
            "{reasons}."
        ),
        "macro.ai_unavailable_result": (
            "Decision: WAIT\nBias: UNKNOWN\nEvent risk: UNKNOWN\nSafe diagnostic: {reasons}\n\n"
            "The provider response was missing, incomplete, or did not satisfy the contract. "
            "A low output limit may truncate a structured response; 1000 tokens is the "
            "recommended value.\n\nNo setting or order was created or modified."
        ),
        "macro.ai_invalid_result": "The AI response does not match the expected contract.",
        "macro.news_refresh": "Refresh market analysis",
        "macro.news_refresh_tooltip": (
            "Bounded Fed/ECB, GDELT and Tavily Basic collection when configured; quota checked."
        ),
        "macro.news_refreshing": "Refreshing market metadata…",
        "macro.news_ready": (
            "{count} item(s) from {providers} provider(s) · collected {timestamp}. "
            "No market sentiment or order signal is inferred."
        ),
        "macro.news_failed": "News coverage unavailable: {reasons}",
        "macro.intelligence.events": "Normalized, deduplicated events",
        "macro.intelligence.sources": "Collected source metadata",
        "macro.intelligence.tavily_highlights": "What Tavily just added",
        "macro.intelligence.tavily_highlights_count": (
            "What Tavily just added — {count} recent result(s)"
        ),
        "macro.intelligence.no_tavily_item": (
            "No Tavily result in this collection. Check activation and refresh."
        ),
        "macro.intelligence.time_unknown": "time not provided",
        "macro.intelligence.show_raw": "Show technical metadata",
        "macro.intelligence.hide_raw": "Hide technical metadata",
        "macro.intelligence.not_collected": "No collection has run yet.",
        "macro.intelligence.contribution": (
            "Visible contribution — Tavily: {tavily} item(s) · official sources: {official} · "
            "GDELT: {gdelt}. Headlines are evidence to review, not trading advice."
        ),
        "macro.intelligence.gdelt_limited": "GDELT · TEMPORARILY RATE LIMITED (HTTP 429)",
        "macro.intelligence.gdelt_network": "GDELT · UNREACHABLE (NETWORK)",
        "macro.intelligence.gdelt_http_error": "GDELT · HTTP SERVICE ERROR",
        "macro.intelligence.gdelt_empty": "GDELT · NO RECENT RESULT",
        "macro.intelligence.gdelt_disabled": "GDELT · DISABLED",
        "macro.intelligence.tavily_empty": "Tavily · NO RECENT RESULT",
        "macro.intelligence.tavily_network": "Tavily · UNREACHABLE (NETWORK)",
        "macro.intelligence.tavily_quota": "Tavily · QUOTA EXHAUSTED",
        "macro.intelligence.tavily_http_error": "Tavily · HTTP SERVICE ERROR",
        "macro.intelligence.tavily_provider_error": "Tavily · UNUSABLE RESPONSE",
        "macro.intelligence.tavily_disabled": "Tavily · NOT CONFIGURED",
        "macro.intelligence.verification": "Verification",
        "macro.intelligence.quota": (
            "Tavily {used}/{limit} · today {today} · remaining {remaining}"
        ),
        "macro.intelligence.freshness": "Freshness · {status}",
        "macro.calendar_explanation": (
            "Tavily and GDELT search published news; they do not provide a structured future "
            "economic calendar. No future event is inferred from their headlines. A dedicated "
            "calendar connector is still required."
        ),
        "macro.context_observed": (
            "Observed factual coverage. No bullish or bearish bias is invented."
        ),
        "macro.context_coverage": (
            "{total} headline(s) across {providers} provider(s) · freshness {freshness}. The "
            "table shows covered themes; market direction stays UNKNOWN until an explicitly "
            "requested analysis."
        ),
        "macro.context.category": "Observed theme",
        "macro.context.items": "Headline count",
        "macro.news.published": "Published",
        "macro.news.source": "Source",
        "macro.news.headline": "Headline",
        "macro.news.category": "Category",
        "macro.news.importance": "Importance",
        "catalogue.busy": "A catalogue search is already running.",
        "catalogue.not_connected": "Connect the read-only DEMO account first.",
        "catalogue.invalid_query": "Search text must contain 3 to 100 characters.",
        "catalogue.context_changed": "Result ignored: the account context changed.",
        "catalogue.cache_invalid": "The local IG inventory is unreadable and was ignored.",
        "stream.start": "Follow selection live",
        "stream.stop": "Stop live feed",
        "stream.not_connected": "Connect a read-only IG account first.",
        "stream.chart_group_degraded": (
            "IG rejected the grouped chart feed; retrying each market separately."
        ),
        "stream.chart_market_unavailable": (
            "Some reference charts are not authorized for this IG account; product quotes "
            "remain active."
        ),
        "stream.price_group_degraded": (
            "IG rejected this quote batch; retrying each market separately."
        ),
        "stream.price_market_unavailable": (
            "One visible product has no stream on this IG account; the other quotes remain active."
        ),
        "stream.product_unknown": "Selection is not in the current catalogue.",
        "stream.unavailable": "The IG account does not expose a streaming endpoint.",
        "stream.state.disconnected": "Live feed stopped — select a product.",
        "stream.state.connecting": "Connecting the feed for {epic}…",
        "stream.state.connected": "Feed connected for {epic}; subscribing…",
        "stream.state.subscribing": "Subscription limited to {epic}…",
        "stream.state.subscribed_waiting_first_tick": (
            "{epic} subscribed — waiting for the first quote."
        ),
        "stream.state.live": "{epic} live — Bid/Offer/Change updated by IG.",
        "stream.state.reconnecting": "Reconnecting the {epic} feed…",
        "stream.state.stale": "The {epic} feed is stalled or stale.",
        "stream.state.failed": "The {epic} feed is unavailable.",
        "stream.state.unknown": "Feed state for {epic}: unknown.",
        "stream.coverage": (
            "IG feed: {subscribed}/39 quote(s), including {priority} permanent priority "
            "market(s), + account · {total} filtered row(s) · state {state}."
        ),
        "stream.short.disconnected": "disconnected",
        "stream.short.connecting": "connecting",
        "stream.short.connected": "connected",
        "stream.short.subscribing": "subscribing",
        "stream.short.subscribed_waiting_first_tick": "waiting for quote",
        "stream.short.live": "live",
        "stream.short.reconnecting": "reconnecting",
        "stream.short.stale": "stale",
        "stream.short.failed": "unavailable",
        "catalogue.column.name": "Market",
        "catalogue.column.live": "●",
        "catalogue.live.header_tooltip": "Quote freshness",
        "catalogue.live.updated": "Quote updated by the current IG stream.",
        "catalogue.live.not_updated": "Quote not updated by the current IG stream.",
        "catalogue.column.epic": "EPIC",
        "catalogue.column.type": "Product",
        "catalogue.column.direction": "Direction",
        "catalogue.column.asset": "Asset class",
        "catalogue.column.bid": "Bid",
        "catalogue.column.offer": "Offer",
        "catalogue.column.change": "Change",
        "catalogue.column.source": "Source",
        "catalogue.column.status": "Status",
        "macro.title": "Market context",
        "macro.empty": "Context unavailable — no data invented",
        "macro.ribbon.news_ready": (
            "Coverage available · {news} item(s) / {providers} provider(s) · "
            "AI analysis unavailable"
        ),
        "macro.ribbon.news_tooltip": (
            "Latest attested collection: {collected}\n"
            "AI status: {reasons}\n"
            "Advisory context only; no execution is triggered."
        ),
        "macro.ribbon.ai_ready": (
            "Bias {bias} · risk {risk} · confidence {confidence} · "
            "{news} item(s) / {providers} provider(s)"
        ),
        "macro.ribbon.ai_tooltip": (
            "Summary: {summary}\nValid until: {validity}\nFlags: {flags}\n"
            "Advisory context only; no execution is triggered."
        ),
        "page.empty.title": "GUI V2 foundation",
        "page.empty.body": (
            "This page is waiting for an attested projection from the single runtime."
        ),
        "page.empty.no_network": "Opening this page does not trigger any network call.",
        "settings.language": "Language",
        "settings.theme": "Theme",
        "tab.overview": "Overview",
        "tab.performance": "Performance",
        "tab.ai_improvement": "AI / Improvement",
        "tab.opportunities": "Opportunities",
        "tab.long": "Long / Bullish",
        "tab.short": "Short / Bearish",
        "tab.watch": "Watch",
        "tab.catalog": "IG Catalog",
        "tab.chart": "Chart",
        "tab.technical": "Technical analysis",
        "tab.ai_analysis": "AI analysis",
        "tab.trade_plan": "Trade plan",
        "tab.market_history": "Market history",
        "tab.open_positions": "Open positions",
        "tab.pending": "Pending",
        "tab.order_history": "Order history",
        "tab.paper": "Simulation",
        "tab.alerts": "Alerts",
        "tab.trade_journal": "Trade journal",
        "tab.pnl": "PnL",
        "tab.statistics": "Statistics",
        "tab.ai_optimization": "AI optimization",
        "tab.news": "News",
        "tab.calendar": "Calendar",
        "tab.global_context": "Global context",
        "tab.ai_snapshots": "AI analyses",
        "tab.service_health": "Service health",
        "tab.flows_quotas": "Streams / quotas",
        "tab.incidents": "Incidents",
        "tab.logs": "Logs",
        "tab.connections": "API & Data Providers",
        "tab.markets": "Markets",
        "tab.strategies": "Strategies",
        "tab.risk": "Risk",
        "tab.ai": "AI",
        "tab.notifications": "Notifications",
        "tab.interface": "Interface",
        "tab.advanced": "Advanced",
    },
}

SUPPORTED_LOCALES = tuple(CATALOGS)
