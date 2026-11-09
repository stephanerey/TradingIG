# Verification

- Project skill validator: 4 local skills valid.
- Generic skill validator limitation: its global `yaml` import is unavailable; no dependency was added because the project validator passed.
- Targeted R06 suite: 34 tests passed.
- Targeted suite including `test_ig_rest_adapter.py`: 46 tests passed; all hard-blocked IG order methods still raise `LiveTradingDisabledError`.
- Full offline suite: `pytest -q` -> 187 passed.
- `ruff check src tests` -> passed.
- Targeted `ruff format --check` on all R06 source and test files -> passed.
- Integration proof covers ticket, trigger, current risk approval, paper fill, confirmed tighter stop, close, reservation release, append-only events and local alert.
- No authenticated IG call, external notification, dependency, migration or DEMO/LIVE activation was added.

Remaining boundary: OHLC/quote paper fills use declared deterministic assumptions and are not evidence of broker realism. ATR/structure/manual trailing variants and persistent external alert delivery are future scoped work, not silently approximated.
