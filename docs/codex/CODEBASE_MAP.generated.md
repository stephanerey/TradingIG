# CODEBASE_MAP.generated.md

> Généré automatiquement. Ne pas éditer manuellement.
> Date: 2026-05-12T18:20:33

## Project metadata

- Root: `C:\PLDesign\Python_Projects\TradingIG`
- Python files: 76
- Project name: `trading-ig-assistant`
- Requires Python: `>=3.11`
- Entry points:
  - `trading-ig-assistant` -> `trading_ig_assistant.main:main`

## Package/source Python files

- `src/trading_ig_assistant/__init__.py`
- `src/trading_ig_assistant/adapters/__init__.py`
- `src/trading_ig_assistant/adapters/credentials.py` — classes: SecretValue, IGCredentials, CredentialStore, InMemoryCredentialStore, KeyringCredentialStore, WindowsCredentialStore | funcs: _coerce_secret, build_default_credential_store
- `src/trading_ig_assistant/adapters/economic_calendar.py`
- `src/trading_ig_assistant/adapters/ig_rest.py` — classes: IGAPIError, LiveTradingDisabledError, IGSession, HttpResponse, HistoricalPriceAttempt, HistoricalPriceFetchResult, HttpClient, UrllibHttpClient | funcs: _case_insensitive_header, is_invalid_security_token_error, is_historical_allowance_error, build_historical_fallback_ladder, load_prices_with_adaptive_fallback, _safe_url_for_log, _optional_float, _market_summary_from_mapping, _format_ig_datetime, _is_malformed_date_error
- `src/trading_ig_assistant/adapters/ig_streaming.py` — classes: StreamingEventSink, IGStreamingAdapter, _ClientListener, _SubscriptionListener, _ChartSubscriptionListener | funcs: _quote_from_update, _epic_from_update, _chart_update_from_update, _first_value, _first_string, _optional_float, _optional_int, build_stream_items
- `src/trading_ig_assistant/adapters/news_provider.py`
- `src/trading_ig_assistant/app/__init__.py`
- `src/trading_ig_assistant/app/application.py` — classes: Application
- `src/trading_ig_assistant/app/config.py` — classes: IGEnvironment, IGConnectionProfileConfig, AppConfig | funcs: load_config, save_config, default_config_path, _normalize_profiles, _default_chart_source_overrides, _normalize_chart_source_overrides
- `src/trading_ig_assistant/app/event_bus.py` — classes: EventBus
- `src/trading_ig_assistant/app/streaming_bridge.py` — classes: StreamingEventBridge
- `src/trading_ig_assistant/domain/__init__.py`
- `src/trading_ig_assistant/domain/journal.py`
- `src/trading_ig_assistant/domain/pending_orders.py`
- `src/trading_ig_assistant/domain/positions.py`
- `src/trading_ig_assistant/domain/products.py` — classes: ProductType, ProductDirection, AssetClass, TradableProduct
- `src/trading_ig_assistant/domain/streaming.py` — classes: StreamState, StreamSubscriptionSpec, StreamDiagnosticResult
- `src/trading_ig_assistant/domain/tickets.py`
- `src/trading_ig_assistant/domain/trade_state.py`
- `src/trading_ig_assistant/main.py` — classes: _DiagnosticStreamSink | funcs: main, build_parser, add_credential_arguments, check_ig_connectivity, discover_products, stream_market, history_market, history_smoke, launch_gui, load_read_only_runtime
- `src/trading_ig_assistant/persistence/__init__.py`
- `src/trading_ig_assistant/persistence/repositories.py`
- `src/trading_ig_assistant/persistence/sqlite_store.py`
- `src/trading_ig_assistant/services/__init__.py`
- `src/trading_ig_assistant/services/analytics_service.py`
- `src/trading_ig_assistant/services/candle_aggregation_service.py` — classes: CandleSeriesUpdated, CandleAggregationService | funcs: live_price_for_quote, price_ohlc_from_payload, chart_scale_for_interval, chart_update_ohlc, _price_timestamp, _bucket_timestamp_ms, _first_decimal, _first_float, _basis_decimal_from_payload, _basis_float_from_payload
- `src/trading_ig_assistant/services/candle_history_service.py` — classes: StreamCacheLoadResult, CandleHistoryService | funcs: _stream_cache_root, _stream_cache_path, _load_stream_candles, _merge_candles, _merge_sources, _bucket_timestamp_ms, _account_marker
- `src/trading_ig_assistant/services/ig_connection_service.py` — classes: IGAccountAdapter, IGConnectionRequest, IGConnectionResult, IGConnectionService | funcs: _account_exists
- `src/trading_ig_assistant/services/journal_service.py`
- `src/trading_ig_assistant/services/macro_context_service.py`
- `src/trading_ig_assistant/services/macro_ribbon_service.py`
- `src/trading_ig_assistant/services/pending_order_engine.py`
- `src/trading_ig_assistant/services/product_discovery_service.py` — classes: ProductDiscoveryAdapter, ProductDiscoveryError, ProductDiscoveryResult, ProductDiscoveryService | funcs: sanitize_payload, discovery_results_to_report, write_discovery_report, read_discovery_report, _mask_identifier, _is_api_allowance_exceeded, _contains_api_allowance_error, _classify_product_type, _classify_direction, _classify_asset_class
- `src/trading_ig_assistant/services/risk_engine.py`
- `src/trading_ig_assistant/services/setup_scoring_service.py`
- `src/trading_ig_assistant/services/ticket_builder.py`
- `src/trading_ig_assistant/services/trade_manager.py`
- `src/trading_ig_assistant/ui/__init__.py`
- `src/trading_ig_assistant/ui/product_selector.py` — classes: ProductSelectorWidget | funcs: _format_number, _format_signed_number, _create_product_table, _matches_product_type, _matches_asset_class
- `src/trading_ig_assistant/utils/__init__.py`
- `src/trading_ig_assistant/utils/ids.py`
- `src/trading_ig_assistant/utils/logging_config.py` — funcs: default_log_dir, default_log_path, configure_logging, emit_session_banner, _find_existing_file_handler
- `src/trading_ig_assistant/utils/redaction.py` — funcs: is_secret_key, redact_value, redact_mapping, redact_text, mask_identifier
- `src/trading_ig_assistant/utils/time.py`

## GUI-related Python candidates

- `src/trading_ig_assistant/ui/about_dialog.py` — classes: AboutDialog | funcs: application_version, _git_short_sha
- `src/trading_ig_assistant/ui/account_status_widget.py` — classes: AccountStatusRibbonWidget | funcs: _select_current_account, _money, _settings_icon
- `src/trading_ig_assistant/ui/chart_view.py` — classes: OhlcBar, TimeAxisMode, ChartDataModel, ChartAxisItem, CandlestickItem, ChartPlotWidget, ChartView | funcs: _format_number, _format_signed_number, _chip_label, _product_anchor_price, _build_placeholder_bars, _bar_from_chart_update, _build_live_price_label, _build_hover_label, _hover_label_html, _bucket_timestamp_ms
- `src/trading_ig_assistant/ui/journal_view.py`
- `src/trading_ig_assistant/ui/log_view_dialog.py` — classes: LogViewDialog
- `src/trading_ig_assistant/ui/macro_ribbon_widget.py` — classes: MacroStatus, MacroStatusChip, MacroRibbonWidget
- `src/trading_ig_assistant/ui/main_window.py` — classes: ActiveIGConnection, CachedHistoryEntry, HistoricalAllowanceState, ResolvedChartSource, ConnectionWorker, ProductDiscoveryWorker, PriceHistoryWorker, MainWindow | funcs: run_gui, _credentials_from_request, humanize_ig_error, _is_api_allowance_exceeded, _api_resolution_for_interval, _history_request_spec, _resolve_account_id, _results_contain_invalid_security_token, _account_id_exists, _first_discovered_product
- `src/trading_ig_assistant/ui/monitor_view.py`
- `src/trading_ig_assistant/ui/settings_dialog.py` — classes: SettingsDialog, ConnectionProfileWidget | funcs: _status_text, _placeholder_tab
- `src/trading_ig_assistant/ui/settings_view.py` — classes: SettingsView | funcs: mask_identifier
- `src/trading_ig_assistant/ui/ticket_view.py`

## Hardware / I/O Python candidates

- `src/trading_ig_assistant/domain/instruments.py` — classes: Account, MarketSummary, MarketCategory, MarketDetails, MarketNavigationNode, MarketNavigation

## Data / ML Python candidates

- `src/trading_ig_assistant/domain/market_data.py` — classes: ChartPriceBasis, CandleSource, Candle, PriceSeries, Quote, ChartCandleUpdate, ChartCandleSeries
- `src/trading_ig_assistant/services/market_data_service.py` — classes: RestMarketDataAdapter, StreamingMarketDataAdapter, MarketDataSnapshot, MarketDataService, _MarketDataStreamSink

## Scripts

- `scripts/codex/generate_python_repo_map.py` — funcs: is_ignored, rel, iter_files, read_pyproject, extract_symbols, categorize_python_files, section_files, main
- `scripts/codex/python_token_run.py` — funcs: compact, main
- `scripts/codex/safe_diff_summary.py` — funcs: run, main
- `scripts/codex/validate_skills.py` — funcs: parse_frontmatter, validate_skill, main
- `scripts/codex/verify_codex_pack.py` — funcs: main

## Tests

- `tests/unit/test_candle_history_service.py` — funcs: test_stream_candle_cache_stores_completed_candles, test_stream_candle_cache_loads_candles_on_startup, test_canonical_series_merges_rest_and_stream_without_duplicates, test_live_stream_update_appends_to_canonical_series, test_stream_cache_file_does_not_store_raw_account_id, json_timestamp_from_content
- `tests/unit/test_config.py` — funcs: test_default_config_is_demo_read_only, test_saved_config_excludes_password_and_api_key, test_config_file_cannot_enable_live_trading_without_explicit_flag, test_profile_config_saves_non_secret_identifiers_only, test_config_persists_last_selected_product_epic, test_config_persists_chart_source_overrides
- `tests/unit/test_credentials.py` — funcs: test_secret_value_redacts_str_and_repr, test_ig_credentials_repr_does_not_leak_secrets, test_redact_mapping_masks_known_secret_keys, test_redact_text_removes_known_secret_values, test_in_memory_credential_store_round_trip
- `tests/unit/test_ig_connection_service.py` — classes: FakeAccountAdapter | funcs: test_connection_service_fetches_accounts_and_logs_out, test_connection_service_switches_to_selected_account, test_connection_service_rejects_email_identifier_before_http
- `tests/unit/test_ig_error_messages.py` — funcs: test_humanize_ig_error_for_invalid_api_key, test_humanize_ig_error_for_invalid_identifier, test_humanize_ig_error_for_client_suspended, test_humanize_ig_error_for_too_many_failed_attempts, test_humanize_ig_error_for_demo_stopbrocking, test_humanize_ig_error_for_api_allowance_exceeded
- `tests/unit/test_ig_rest_adapter.py` — classes: FakeHttpClient | funcs: test_login_and_read_only_calls_use_demo_base_url, test_order_execution_methods_are_hard_blocked_in_p00, test_switch_account_reuses_new_security_token, test_market_navigation_uses_hyphenated_endpoint, test_categories_and_category_instruments_are_read_only, test_logout_ignores_invalid_security_token, test_get_prices_max_points_mode_uses_expected_path, test_get_prices_falls_back_from_malformed_date_to_max_points, test_build_historical_fallback_ladder_skips_larger_values, test_is_historical_allowance_error_matches_ig_error_code
- `tests/unit/test_ig_streaming_adapter.py` — classes: FakeConnectionDetails, FakeLightstreamerClient, FakeUpdate, RecordingSink | funcs: test_streaming_adapter_connects_and_parses_quotes, test_streaming_adapter_emits_chart_updates, test_streaming_adapter_subscribes_multiple_market_prices, test_stream_item_template_generation_supports_market_and_chart, test_quote_parser_supports_market_style_fields, test_quote_parser_supports_price_style_fields, test_chart_parser_supports_chart_subscription_item, test_streaming_adapter_reports_missing_endpoint
- `tests/unit/test_logging_config.py` — funcs: test_configure_logging_creates_weekly_rotating_file_handler, test_emit_session_banner_writes_separator
- `tests/unit/test_main_cli.py` — funcs: test_main_without_arguments_launches_gui, test_main_help_still_prints_usage, test_stream_market_redacts_account_and_secrets, test_history_market_reports_fallback_attempts, test_history_market_accepts_multiple_epics, test_history_market_can_switch_account, test_history_smoke_stops_after_allowance_error
- `tests/unit/test_market_data_service.py` — classes: FakeRestAdapter, FakeStreamingAdapter | funcs: test_market_data_service_loads_history_and_emits_updates, test_market_data_service_handles_stream_lifecycle_and_stale_detection, test_live_price_for_quote_uses_selected_basis, test_chart_update_mid_basis_averages_bid_and_offer_fields, test_historical_price_conversion_uses_selected_basis
- `tests/unit/test_product_discovery_service.py` — classes: FakeDiscoveryAdapter, EmptyNavigationAdapter, CategoryDiscoveryAdapter, AllowanceExceededNavigationAdapter | funcs: test_classification_heuristics_identify_barrier_and_option, test_sanitized_report_excludes_sensitive_values, test_discovery_report_round_trips_results, test_discover_all_products_uses_market_navigation, test_discover_all_products_prefers_enabled_categories, test_discover_all_products_falls_back_to_search_when_navigation_unavailable, test_discover_all_products_stops_after_allowance_exceeded, test_crypto_discovery_seeds_cover_ig_crypto_barrier_tab
- `tests/unit/test_ui_shell.py` — funcs: test_gui_modules_import_without_ig_connectivity, test_chart_model_accepts_sample_ohlc_data, test_chart_model_builds_bars_from_price_series, test_history_request_spec_targets_longer_windows, test_chart_view_defaults_to_five_minutes_internally, test_chart_scale_for_interval_uses_true_five_minute_stream, test_chart_view_history_range_selector_emits_changes, test_chart_view_accepts_live_quote_update, test_chart_view_live_line_uses_selected_price_basis, test_price_basis_change_reloads_selected_product_history_once

## Other Python files

- _none detected_

## Config/runtime files

- `pyproject.toml`

## Resource/config candidates

- `docs/codex/PROJECT_PROFILE.yaml`
- `pyproject.toml`
