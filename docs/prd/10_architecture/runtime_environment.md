# Runtime Environment

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Original text is preserved; documented V1.2 changes govern current scope. No implementation or activation is implied.


> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-10-22

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

## V1.2 scope alignment

Target Windows 11, PyQt5/PyQtGraph; Python 3.12 requires qualification. Existing pyproject.toml requires >=3.11. No dependencies have been installed or qualified here. WSL execution is not native Windows GUI evidence.

Canonical requirements: [chapter 2](../01_product/decisions.md), [chapter 12](../30_feature/F012_windows_workspace_and_settings.md), [chapter 16](security_and_auth.md).
