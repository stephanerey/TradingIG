# Verification

Date: 2026-05-12

## Commands Already Run In This Pass

Workspace verification:

```powershell
Set-Location -LiteralPath "C:\PLDesign\Python_Projects\TradingIG"; Get-Location; Get-ChildItem -Force | Select-Object Name,Mode,Length; git status; git log --oneline -5; git remote -v; Test-Path "docs\codex\TradingIG_RECOVERY_CONTEXT.md"
```

Read-only inspection commands included:

```powershell
git log --oneline -10
git show --stat --oneline --decorate --no-renames -5
git show --name-status --oneline b6b964a
git show --name-status --oneline 936e8cc
rg --files src tests docs
rg -n "(?i)(historical|history|candle|stream|cache|Lightstreamer|CHART|PRICE|allowance)" src tests docs\spikes\P02_streaming_diagnostics.md
```

## Not Run Yet

No post-documentation test suite was run in this pass.

## Recommended Local Verification

For code health:

```powershell
python -m pytest
python -m ruff check src tests
```

For the proposed future price-basis patch:

```powershell
python -m pytest tests/unit/test_ui_shell.py tests/unit/test_candle_history_service.py tests/unit/test_ig_rest_adapter.py
python -m ruff check src tests
```

For manual IG history diagnostics, with credentials provided through environment variables:

```powershell
trading-ig-assistant history-smoke --environment live --epic IX.D.NASDAQ.IFD.IP
trading-ig-assistant history-market --environment live --epic IX.D.NASDAQ.IFD.IP --resolution MINUTE_5 --max-points 120 --account-id <account-id>
```

For streaming diagnostics, with credentials provided through environment variables:

```powershell
trading-ig-assistant stream-market --environment live --epic IX.D.NASDAQ.IFD.IP --duration 30
```

## Verification Risks

- Live/demo IG results depend on account permissions, market state, rate limits, and session state.
- Historical allowance errors may be account-scoped and time-window dependent.
- GUI tests require PyQt5 availability and can be sensitive to local Qt platform setup.
