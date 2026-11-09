# Verification

```text
Focused config/Scanner/navigation/UI suite: 48 passed in 3.81s
Protected Paper/risk/ticket/DEMO regressions: 79 passed in 0.40s
Full offline suite: 552 passed in 26.38s
ruff check src tests: passed
Targeted ruff format --check: 2 files already formatted
SR Method 4.1 pack verification: coherent
git diff --check: no whitespace error; pre-existing LF-to-CRLF warnings only
```

No authenticated request, ticket, broker command or order was exercised.

## Post-validation correction

The first human LIVE check failed with
`CHART:IX.D.CAC.IMF.IP:1MINUTE: -1 Insufficient permissions`, while direct Barrier quotes kept
arriving. A bounded quote-candle fallback was added without treating product prices as reference
market data.

```text
Focused quote-fallback/UI suite: 59 passed
Protected ticket/risk/Paper/connection/DEMO-gate regressions: 78 passed
Full offline suite: 556 passed in 27.07s
ruff check src tests: passed
git diff --check on changed Python/tests: passed
```

After restart, the user reported that a candle appeared. This confirms initial display only; it
does not establish continuity, OHLC accuracy over time, or reference-market Scanner availability.
No order or authenticated request was initiated by the correction.

Follow-up subscription-priority change: `tests/unit/test_ui_shell.py` 56 passed; targeted Ruff
passed. The user-started session returned `PRICE: 21 Invalid group` for the grouped subscription,
so the priority change was reverted. The error does not identify the offending item. The reference
PRICE entitlement remains unproven and the Scanner is not fed from those quotes.

An isolated one-item reference PRICE probe now runs only after the selected reference CHART is
denied. Its rejection or updates are logged separately, do not replace the main price subscription,
and are not passed to the Scanner. A fake-client regression verifies isolation and cleanup;
557 offline tests and repository src/tests Ruff checks passed. On the user-started LIVE session,
the isolated `PRICE` probe for `IX.D.CAC.IMF.IP` returned `21 Invalid group`; selected Barrier
quotes continued afterwards. This establishes rejection of that PRICE request, not the precise
reason for rejection or whether a different IG quote subscription is available.

The isolated diagnostic now tries the existing `MARKET` subscription instead of the rejected
`PRICE` item. It remains separate from product prices, does not send updates to the Scanner, and
records first received quote or rejection. Full offline suite: 557 passed; Ruff src/tests passed.
Real-session MARKET observation remains pending.

User-started LIVE observation: isolated `MARKET:IX.D.CAC.IMF.IP` was rejected with `21 Invalid
group`; no conclusion is drawn about other EPICs or other account permissions.

Follow-up: option variation snapshot/live regression and the remaining suite passed: 558 tests;
53 protected Paper/risk/ticket/DEMO-gate tests passed; Ruff src/tests passed. Automatic MARKET
probing is disabled. Windows visual confirmation of the selector change has not been performed.

Quote-candle follow-up: 84 focused data/stream/UI tests, 53 protected Paper/risk/ticket/DEMO-gate
tests and 560 full offline tests passed; Ruff src/tests passed. A new Windows session is needed to
observe actual IG updates; no broker request was initiated during offline testing.

User-started Windows session 2026-11-06 13:13–13:23: direct France Barrier quotes were still
arriving at the end of this interval and the selected-chart fallback activated. This is evidence
of ongoing receipt, not proof that each quote was received, correctly timestamped, or that the
rendered OHLC exactly matches a reference dataset. IG continued to reject the reference CHART.

Account/environment isolation: 74 focused data/UI tests, 53 protected tests and 561 full offline
tests passed; Ruff src/tests passed. The LIVE reference refusal's cause remains unproven.

DEMO France CFD: user screenshot plus logs confirm IG CHART updates for exact reference EPIC.
Its self-binding and synthetic DEMO Scanner batch pass, alongside 39 focused tests, 53 protected
tests and 562 full offline tests. Windows Scanner warmup/preview remains to be checked.

Option chart header: snapshot and live option variation suppression, tooltip, unaffected quote
display and return to normal for a CFD chart are covered; 563 full and 53 protected tests passed,
Ruff src/tests passed. The active user DEMO session was not interrupted or restarted.

Streaming error-scope follow-up: 70 UI/adapter targeted tests, 53 protected tests and 564 full
offline tests passed; Ruff src/tests passed. PRICE permission errors and mismatched chart groups
do not reset the scanner router or retry chart subscriptions; matching CHART failure still does.

Account/connection state follow-up: 91 targeted UI/ticket/stream tests, 53 protected tests and
568 full offline tests passed; Ruff src/tests passed. Tests cover queued old-generation callbacks,
successful and failed account switches, Paper evaluation invalidation and Scanner clearing. The
ongoing user DEMO session was not interrupted; Windows grouped validation remains pending.
The UI also rejects an adapter switch result identifying a different account (86 focused UI,
ticket and connection tests passed). The current IG adapter constructs its returned account ID
from the requested ID after HTTP success, so this check alone is not independent IG confirmation.

Human DEMO CFD screenshot: France 40 `IX.D.CAC.IMF.IP`, M1, 26 closed candles and three technical
Scanner rows displayed. Context, risk and costs were unknown, and total score unavailable; no
ticket or order was created. The large wick around 14:30 appears in IG CHART logs as well; those
logs alone do not establish whether it was a true market move or a feed anomaly. Data-quality
tooltip now states that the score does not independently validate prices or detect outliers.
11 focused Scanner UI tests, 53 protected tests and 570 full offline tests passed; Ruff passed.

Quote log/display follow-up: 97 UI/ticket/stream/log tests, 53 protected tests and 572 full
offline tests passed; Ruff src/tests passed. Synthetic tests verify account masking, unchanged
wire subscriptions, filter repaint and unchanged Paper quote-receipt timestamp. Existing log files
were not modified. Grouped Windows validation is pending at the user's convenience.

Explicitly delayed quotes: 65 focused ticket/Paper/Scanner/stream tests, 55 protected tests and
576 full offline tests passed; Ruff src/tests passed. Synthetic tests cover delayed approval
invalidation, no target/manual close, unknown mark, resumed non-delayed operation and unavailable
Scanner spread. This does not establish freshness when IG supplies no recognizable delay flag.

Freshness/connection isolation follow-up: 121 focused UI/Scanner/Paper tests, 57 protected tests
and 580 full offline tests passed; Ruff, format check and targeted diff check passed. Tests cover
30/31-second boundaries, future timestamps, delayed data, stale restored positions, explicit
connection invalidation and resumption with a new quote. Current GUI has no periodic refresh when
the Paper tab is left open without ticks; closing remains guarded at action time. Grouped Windows
validation is pending; no IG request or order was initiated in these checks.

Human grouped-validation update: the user saved an open Paper position, exited and restarted the
application, restored the position and observed it updating again. This confirms the reported
restore/resumption path, not the stale-quote timeout, filtering or account-switch edge cases.
The user subsequently disconnected and reconnected and reported that Paper updates resumed.
The user did not explicitly report the mark state during the disconnected interval.

