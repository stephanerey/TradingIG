# Secure API credentials

TradingIG separates provider activation and test metadata from secret material.

## Resolution priority

For each stable provider identifier (`ig`, `tavily`, `gdelt`, `fred`, `eia`,
`openai`), `ApiCredentialManager` resolves credentials in this order:

1. operating-system keyring (`trading-ig-assistant-api-providers` service);
2. the provider-specific environment variable (`IG_API_KEY`, `TAVILY_API_KEY`,
   `FRED_API_KEY`, `EIA_API_KEY`, or `OPENAI_API_KEY`);
3. public access for providers that do not require a key (currently GDELT).

Deleting a key from Settings removes only the keyring entry. If an environment
variable is still defined, it becomes the active fallback and is shown as such.

## Storage boundary

`config.json` stores only non-secret activation flags and the timestamp of the last
successful explicit connection test. API keys are never written to JSON, YAML,
SQLite, task evidence, exception text, or logs. Tests use an in-memory key store.

Connection probes run only after an explicit click and execute on a Qt worker thread.
Tavily's probe is a bounded Basic search and may consume one credit; the UI states this
beforehand. No subscription, billing action, order, LIVE execution, or automatic
connection test is initiated by the credential manager.
