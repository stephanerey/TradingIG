# Findings - stream live candle robustness

## Chemin complet verifie

1. Lightstreamer est encapsule par `IGStreamingAdapter`.
   - `subscribe_markets()` cree une subscription `PRICE:{account_id}:{epic}` via `PRICE_QUOTE_SPEC`.
   - `subscribe_chart()` cree une subscription `CHART:{epic}:{scale}` via `CHART_CANDLE_SPEC`.
   - Les callbacks Lightstreamer appellent `_SubscriptionListener.onItemUpdate()` ou `_ChartSubscriptionListener.onItemUpdate()`.
   - Les payloads sont normalises par `_quote_from_update()` et `_chart_update_from_update()`.

2. Les callbacks sortent de l'adapter par `StreamingEventSink`.
   - Quotes: `IGStreamingAdapter._handle_quote_update()` -> `event_sink.on_quote(quote)`.
   - Candles chart: `IGStreamingAdapter._handle_chart_update()` -> `event_sink.on_chart(chart_update)`.

3. Dans l'UI, `MainWindow` donne `StreamingEventBridge` comme sink.
   - `StreamingEventBridge` transforme les callbacks de fond en signaux Qt.
   - `quote_received` est connecte a `MainWindow._on_stream_quote()`.
   - `chart_received` est connecte a `MainWindow._on_stream_chart()`.

4. Les quotes mettent a jour les labels/live line.
   - `_on_stream_quote()` pousse la quote dans `ProductSelectorWidget`.
   - Si l'EPIC correspond au chart product, la quote va aussi dans `ChartView.set_live_quote()`.

5. Les chart updates alimentent les candles canoniques.
   - `_on_stream_chart()` filtre sur le `chart_product`.
   - Puis appelle `CandleHistoryService.apply_stream_update()`.
   - `CandleHistoryService` appelle `CandleAggregationService.apply_chart_update()`.
   - La serie renvoyee est stockee dans `MainWindow._chart_candle_series`.
   - L'UI est rafraichie par `ChartView.set_candles(chart_series.candles, preserve_view=True)`.
   - Une quote synthetique est derivee par `_quote_from_chart_update()` pour mettre a jour la live line.

## Ecriture du stream-cache

- L'ecriture est dans `CandleHistoryService._persist_closed_candle()`.
- Elle est declenchee par `CandleHistoryService.apply_stream_update()` uniquement si `chart_update.end_of_candle` est vrai et `chart_update.timestamp_ms` non nul.
- Le chemin disque est construit par `_stream_cache_path()`:
  - racine par defaut: `Path.home() / ".trading_ig_assistant" / "cache" / "stream_candles"`;
  - sous-dossier: `{environment.value}/{sha1(account_id)[:12]}/`;
  - fichier: `{safe_chart_source_epic}__{resolution_seconds}s__{price_basis.value}.jsonl`.
- Le payload ecrit contient `environment`, `chart_source_epic`, `interval_seconds`, `price_basis`, `source`, `timestamp`, OHLC et volume. Il ne contient pas l'account id brut.

## Relecture du stream-cache

- `MainWindow._load_selected_product_history()` appelle `CandleHistoryService.load_stream_cache()` pour chaque candidat de `history_candidates`.
- Cette lecture est faite au demarrage indirectement quand `_load_cached_discovery_results()` restaure `last_selected_product_epic` puis appelle `_on_product_selected()`, qui appelle `_apply_selected_product_state()`, puis `_load_selected_product_history()`.
- Elle est aussi faite au changement de produit via `_on_product_selected()` -> `_apply_selected_product_state()` -> `_load_selected_product_history()`.
- Elle est faite au changement de resolution, range et price basis via les handlers de `ChartView`.
- `load_stream_cache()` active une serie correspondant a selected EPIC + chart source EPIC + resolution + price basis, lit le JSONL, dedoublonne par timestamp ISO et fusionne avec la serie courante en preferant l'entrant.

## Risques identifies

1. Prioritaire: le stream-cache peut etre ignore si `_api_allowance_exceeded` est vrai.
   - Dans `MainWindow._load_selected_product_history()`, la boucle qui charge `load_stream_cache()` commence apres le `return` global `_api_allowance_exceeded`.
   - Donc un blocage global d'API peut empecher l'affichage de candles stream deja disponibles, alors que cette lecture est locale et independante du REST historique.
   - Les tests couvrent le cas `HistoricalAllowanceState.exhausted`, mais pas explicitement `_api_allowance_exceeded=True` avec stream-cache disponible.

2. Le fichier JSONL peut grossir avec des doublons persistants.
   - En memoire et a la relecture, les candles sont dedoublonnees par timestamp.
   - Mais `_persist_closed_candle()` append a chaque `CONS_END` sans compaction ni remplacement de ligne existante.
   - Impact: pas de doublon affiche apres reload, mais croissance disque et cout de lecture inutiles.

3. Timestamp: le flux UI et le cache bucketent sur `resolution_seconds`.
   - `CandleAggregationService.apply_chart_update()` bucket le `timestamp_ms` si `interval_seconds` est fourni.
   - `_persist_closed_candle()` recherche la candle fermee sur le bucket.
   - Risque limite: si `UTM` Lightstreamer represente deja une borne differente selon l'echelle, le bucket local peut associer la candle a une borne differente de celle attendue. Le code et les tests supposent actuellement que le bucketing est correct.

4. Price basis: la separation par fichier limite les melanges.
   - Le chemin inclut `price_basis.value`.
   - `apply_stream_update()` reconstruit OHLC selon le basis courant.
   - `ChartView.set_candles()` affiche des `Candle` deja converties, donc le changement de basis doit recharger la serie. C'est prevu par `_on_chart_price_basis_changed()`.
   - Risque residuel: si une chart update ne contient qu'un seul cote ou seulement `close`, les helpers retombent sur la valeur disponible. C'est volontaire dans `_basis_*_value()`, mais cela peut produire une serie "bid/ask" partiellement approximative.

5. Local aggregation fallback: la variable `_aggregation_mode` est descriptive.
   - En cas d'erreur sur une echelle chart non 1-minute, `_on_stream_error()` se rabat sur `subscribe_chart(..., "1MINUTE")`.
   - `apply_stream_update()` bucket ensuite les updates 1-minute vers la resolution UI.
   - Ce n'est pas une vraie aggregation OHLC multi-candle: quand plusieurs updates 1-minute tombent dans le meme bucket de 5 minutes, `CandleAggregationService.apply_chart_update()` remplace la candle par la derniere candle 1-minute au lieu de composer open/high/low/close sur tout le bucket.

## Patch minimal prioritaire propose

Ne pas toucher a REST ni a `IGRestAdapter`.

Patch propose:
- Dans `MainWindow._load_selected_product_history()`, charger et afficher le stream-cache avant le retour `_api_allowance_exceeded`.
- Si `_api_allowance_exceeded` est vrai, ne pas lancer de requete REST, mais conserver l'affichage du stream-cache deja charge si present.
- Ajouter un test UI cible: stream-cache disponible + `_api_allowance_exceeded=True` + adapter REST qui echoue si appele => `chart_view.display_bar_count() > 0`, source `CACHE`, aucun appel REST.

Patch secondaire, apres validation:
- Rendre l'agregation locale 1-minute -> N-minutes cumulative dans `CandleAggregationService.apply_chart_update()` quand `chart_update.interval == "1MINUTE"` et `resolution_seconds > 60`: open du premier sous-bucket, high max, low min, close du dernier.
- Ajouter un test unitaire avec deux updates 1-minute dans le meme bucket 5-minute.
