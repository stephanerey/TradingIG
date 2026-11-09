# R02 findings

- The existing market-data service defined local REST/streaming protocols, while the PRD required reusable provider and broker contracts plus explicit instrument provenance.
- The IG REST/streaming implementations already provided compatible market-data methods; adding a stable `provider_id` and importing the canonical protocols preserved behavior without relocation.
- The IG REST adapter now reports only discovery/account-read capabilities as supported. Order, stop, close, pending, KO and demo/live execution capabilities remain explicitly `UNSUPPORTED`; existing hard-blocked order methods are unchanged.
- `InstrumentMappingRegistry` resolves only exact `(provider_id, instrument_id)` keys and can group equivalent canonical instruments without assuming equal execution prices.
- Account scope mismatch raises a normalized domain error without exposing account identifiers. `UNKNOWN` execution results require reconciliation and are never treated as confirmation.
- The window-size issue came from aggregate child minimum-size hints (about 3259×699), mainly the macro ribbon and splitter panels. Making only the containing layout/ribbons/splitter panels compressible reduced the effective hint to 0×115 and allowed 960×600 without redesigning the interface.
