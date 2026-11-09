# Verification

```text
Focused Scanner runtime/UI/core suite: 24 passed in 3.35s
Protected Paper/risk/ticket/DEMO regressions: 79 passed in 0.43s
Full offline suite: 551 passed in 26.37s
ruff check src tests: passed
Targeted ruff format --check: 5 files already formatted
SR Method 4.1 pack verification: coherent
git diff --check: no whitespace error; pre-existing LF-to-CRLF warnings only
```

No network call, ticket, broker command or order was exercised.

## Human Windows validation

On 2026-11-06 the user refreshed the LIVE Scanner after 44 session M1 candles. The provisional
table displayed the three strategies for `IX.D.NASDAQ.OPTCALL2.IP`, including a ready BUY
`trend_follow` signal and explicit unknown context/risk/cost degradation. No ticket or order action
was present.

