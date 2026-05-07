# Trading IG Assistant

Python desktop application skeleton for assisted trading with IG.

This repository is currently in **P00 Bootstrap**. It contains only the safe foundation:
configuration, credential redaction, read-only IG REST adapter scaffolding, and tests.

## Safety status

Live trading is **not implemented**.

The P00 adapter contains no functional order execution path. Any create/update/close order
method currently raises a live-trading-disabled error. Use demo/read-only mode first.

## Setup

```powershell
cd C:\PLDesign\Python_Projects\TradingIG
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

Optional secure keyring support:

```powershell
python -m pip install -e .[secure-store,dev]
```

## Run tests

```powershell
pytest
ruff check src tests
```

## Read-only IG connectivity check

Create or load a non-secret JSON config. Passwords and API keys must not be saved in that file.
Provide secrets through environment variables for the connectivity check:

```powershell
$env:TRADING_IG_USERNAME="your-demo-username"
$env:TRADING_IG_PASSWORD="your-demo-password"
$env:TRADING_IG_API_KEY="your-demo-api-key"

trading-ig-assistant check-ig-connectivity `
  --environment demo `
  --username-env TRADING_IG_USERNAME `
  --password-env TRADING_IG_PASSWORD `
  --api-key-env TRADING_IG_API_KEY `
  --search "US Tech"
```

The command authenticates, fetches accounts, and can optionally perform read-only market search,
market details, and historical prices calls.

## Project layout

The package follows `docs/prd/10_architecture/package_layout.md`. Broker-facing code is isolated
under `src/trading_ig_assistant/adapters/`, UI modules stay thin placeholders, and core/domain
modules remain importable without Qt or IG connectivity.
