# Findings

- The adapter already supported one deduplicated multi-item chart subscription, but the Qt runtime
  still called the single-chart compatibility method.
- The provisional chart renderer filters updates by the selected chart-source EPIC, so reference
  updates can be accumulated before that filter without changing the visible chart.
- `CandleHistoryService.apply_session_m1_update` keeps all price bases in process memory and performs
  no disk access; a dedicated instance avoids coupling the Scanner's shared reference series to the
  displayed chart's active series.
- The first DEMO GUI smoke authenticated successfully but then sent `switch_account` for the account
  already active in the login response. IG correctly rejected that redundant request with HTTP 412
  `error.switch.accountId-must-be-different` before streaming initialization.
- A later LIVE reconnect authenticated but IG rejected the grouped chart subscription with
  Lightstreamer `-1 Insufficient permissions`. Because all references shared one subscription, the
  refusal also stopped the selected chart candle stream.
