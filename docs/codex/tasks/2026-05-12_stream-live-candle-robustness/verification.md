# Verification - stream live candle robustness

## Effectue

- Lecture des documents projet demandes.
- Lecture ciblee des modules:
  - `src/trading_ig_assistant/adapters/ig_streaming.py`
  - `src/trading_ig_assistant/app/streaming_bridge.py`
  - `src/trading_ig_assistant/domain/market_data.py`
  - `src/trading_ig_assistant/domain/streaming.py`
  - `src/trading_ig_assistant/services/candle_aggregation_service.py`
  - `src/trading_ig_assistant/services/candle_history_service.py`
  - `src/trading_ig_assistant/services/market_data_service.py`
  - `src/trading_ig_assistant/ui/main_window.py`
  - `src/trading_ig_assistant/ui/chart_view.py`
- Lecture ciblee des tests:
  - `tests/unit/test_candle_history_service.py`
  - `tests/unit/test_market_data_service.py`
  - `tests/unit/test_ig_streaming_adapter.py`
  - `tests/unit/test_ui_shell.py`
- `git status --short -uall`: seuls les fichiers de cette memoire de tache sont non suivis.
- `git diff --name-only -- src tests AGENTS.md docs/CURRENT_STATE.md docs/codex/PROJECT_PROFILE.yaml docs/codex/SKILL_MAP.md docs/codex/CODEBASE_MAP.md docs/codex/CODEBASE_MAP.generated.md`: aucune sortie.

## Non execute

- Pas de tests lances: analyse lecture seule, pas de modification applicative, et eviter les ecritures de caches pytest.
