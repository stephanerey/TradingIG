# Findings

- `ScannerProfilePatch` existed only in the resolver and had no durable representation.
- `AppConfig` persisted scanner costs and scoring, but no strategy profile catalog.
- `SettingsDialog.updated_config()` reconstructs `AppConfig`, so a non-visual catalog must be
  copied explicitly or it would be lost when settings are applied.
- `TradableProduct` does not expose a canonical underlying ID. This task therefore requires an
  explicit canonical key and does not infer one from an expiring Barrier/Option EPIC.
- R02 already defines `InstrumentMappingRegistry`; the profile bridge now consumes its explicit
  `underlying_id` and fails closed when the provider instrument is unmapped.

