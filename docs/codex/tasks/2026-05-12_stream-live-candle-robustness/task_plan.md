# Task plan - stream live candle robustness

## Objectif verifiable
Analyser en lecture seule la chaine Lightstreamer -> ticks/prices -> aggregation candles -> chart UI, puis proposer un patch minimal prioritaire sans modifier le code applicatif.

## Skills declares
- python-planning-with-files
- python-data-pipeline
- python-pyqt-threading
- python-review-diff

## Fichiers a lire
- AGENTS.md
- docs/CURRENT_STATE.md
- docs/codex/PROJECT_PROFILE.yaml
- docs/codex/SKILL_MAP.md
- docs/codex/CODEBASE_MAP.md
- docs/codex/CODEBASE_MAP.generated.md
- src/trading_ig_assistant/adapters/ig_streaming.py
- src/trading_ig_assistant/app/streaming_bridge.py
- src/trading_ig_assistant/services/candle_aggregation_service.py
- src/trading_ig_assistant/services/candle_history_service.py
- src/trading_ig_assistant/services/market_data_service.py
- src/trading_ig_assistant/domain/market_data.py
- src/trading_ig_assistant/ui/main_window.py
- src/trading_ig_assistant/ui/chart_view.py
- tests/unit/test_ig_streaming_adapter.py
- tests/unit/test_market_data_service.py
- tests/unit/test_candle_history_service.py
- tests/unit/test_ui_shell.py

## Fichiers candidats a modifier plus tard
- A determiner apres analyse. Aucun fichier applicatif ne sera modifie pendant cette tache.

## Verification prevue
- Lecture ciblee du code et des tests.
- `git diff -- docs/codex/tasks/2026-05-12_stream-live-candle-robustness`
- `git status --short`
- Pas de tests applicatifs requis pour cette analyse lecture seule.

## Hors perimetre
- Backfill REST historique.
- Allowance history et retry historique.
- IGRestAdapter.
- Credentials.
- Appels IG live/demo.
- Refactor global.
