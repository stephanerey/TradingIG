# R02 verification

| Check | Result |
|---|---|
| Laptop resize regression | PASS — `MainWindow` accepts 960×600; effective minimum hint 0×115 |
| Adapter-contract focused suite | PASS — two fake historical providers, streaming protocol, mappings, account scope, capabilities and ambiguous outcomes |
| IG safety regression | PASS — `LiveTradingDisabledError` order-path test unchanged and green |
| Focused adapter/market/UI suite | PASS — 36 tests |
| Full offline suite | PASS — 113 tests |
| `ruff check src tests` | PASS |
| RepoMap refresh | PASS — generated map includes `domain/adapter_contracts.py` and its contract types |
| Manual connected smoke | PASS (user-reported) — LIVE connection and crude-oil candle arrival; no authenticated action performed by Codex |

## Limits

- Contract tests use synthetic/fake providers; they do not certify execution support at IG.
- The interface is now shrinkable but intentionally not redesigned; content may become compressed at small sizes until the planned UI revision.
- No dependency, migration, credential read, broker order, or R03/R04 settings decision was introduced.
