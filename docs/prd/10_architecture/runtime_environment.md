# Runtime Environment

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

## Goal
Define a reproducible local desktop environment for development and execution.

## Target platform
- Primary: Windows desktop.
- Secondary: Linux/WSL for development and tests where no GUI is required.

## Python/tooling
- Python 3.12+ recommended.
- Package layout: `src/`.
- Testing: `pytest`.
- Formatting/linting: `ruff` recommended.
- Type checking: `mypy` or `pyright` recommended.
- UI: PyQt5/PySide6 to be decided during P00/P20; core logic MUST not depend on Qt.
- Charting: pyqtgraph preferred for live candlestick rendering.
- Persistence: SQLite.
- Secrets: OS keyring via Python `keyring` package or platform-specific secure storage.

## External connectivity
- IG REST API over HTTPS.
- IG Streaming API via Lightstreamer client.
- News/calendar providers via HTTP APIs or RSS feeds.

## Constraints
- App must run without IG credentials in unit-test mode.
- Integration tests requiring IG credentials must be explicitly skipped unless environment variables or secure test settings are provided.

## Acceptance criteria
- `pip install -e .[dev]` works.
- `pytest` works without real credentials.
- First demo integration test is separately documented.

## Testing notes
- Mock HTTP and streaming adapters in CI/local unit tests.
