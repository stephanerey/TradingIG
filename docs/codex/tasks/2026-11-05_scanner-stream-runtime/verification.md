# Verification

## Targeted

```text
python -m ruff check <modified runtime and test files>
All checks passed!

python -m pytest tests/unit/test_ui_shell.py
  tests/unit/test_multi_market_session_candle_service.py
  tests/unit/test_ig_streaming_adapter.py tests/unit/test_config.py
  tests/unit/test_market_navigation_catalog_service.py -q
101 passed in 13.58s
```

## Final offline gates

```text
Protected IG/DEMO/risk/ticket/Paper selection: 51 passed in 0.42s
Connection/UI regression suite after the DEMO failure: 58 passed in 16.58s
Full offline suite after the fix: 544 passed in 27.69s
ruff check src tests: passed
Targeted ruff format --check: 6 files already formatted
SR Method 4.1 pack verification: coherent
git diff --check: no whitespace error; pre-existing LF-to-CRLF warnings only
```

## Grouped-stream permission fallback

```text
Targeted UI/stream/session-candle suite: 70 passed in 14.28s
Full offline suite: 546 passed in 24.33s
ruff check src tests: passed
Targeted ruff format --check: 2 files already formatted
SR Method 4.1 pack verification: coherent
git diff --check: no whitespace error; pre-existing LF-to-CRLF warnings only
```

## Human boundary

The user validated the read-only GUI on DEMO on 2026-11-05. Logs also prove one successful LIVE
connection at 18:07:42 with account discovery and active five/six-item M1 subscriptions; exact
updates were received for US Tech, France 40, Germany 40, Gold and US Crude. No order was placed.

An application restart six seconds after a clean LIVE logout produced a second successful session
login followed by IG HTTP 401 `error.security.client-token-invalid` on `GET /accounts`. This does
not invalidate the preceding LIVE stream proof and was not converted into an automatic auth retry.

A later LIVE reconnect exposed Lightstreamer `-1 Insufficient permissions` on the grouped chart
subscription. The runtime now retries once with only the selected chart source, leaving the
multi-market Scanner explicitly degraded. On 2026-11-06 the user relaunched LIVE and saw the
degraded-Scanner message; runtime logs then confirmed continuous M1 chart updates for the selected
`IX.D.NASDAQ.IFD.IP` source after the fallback. No order was attempted.
