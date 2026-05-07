# Trading IG Assistant

Python desktop application skeleton for assisted trading with IG.

This repository is currently in **P02 streaming foundation**. It contains the safe bootstrap,
read-only IG product discovery, a minimal GUI shell, a candlestick chart placeholder, and a
first Lightstreamer live-quote path for the selected product.

## Safety status

Live trading is **not implemented**.

The adapter contains no functional order execution path. Any create/update/close order or
working-order method currently raises a live-trading-disabled error. Use demo/read-only mode first.

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

## Read-only product discovery

Run discovery for one or more search terms:

```powershell
trading-ig-assistant discover-products `
  --environment demo `
  --username-env TRADING_IG_USERNAME `
  --password-env TRADING_IG_PASSWORD `
  --api-key-env TRADING_IG_API_KEY `
  --search "US Tech 100" `
  --output .\product_discovery.local.json
```

Run discovery for the initial watchlist:

```powershell
trading-ig-assistant discover-products --watchlist --output .\watchlist.local.json
```

Discovery output is sanitized and intended for analysis. Do not commit local discovery reports.

## GUI shell

Launch the minimal P01 GUI:

```powershell
trading-ig-assistant gui
```

Direct execution also launches the GUI, which is convenient from an IDE run configuration:

```powershell
python .\src\trading_ig_assistant\main.py
```

Debug logs are written to `%USERPROFILE%\.trading_ig_assistant\logs\trading_ig_assistant.log`.
The file rotates daily and keeps seven days of history. In the GUI, use `Help > View log` to open
the current log file.

The GUI includes a main window, menu bar, macro context ribbon placeholder, candlestick chart
placeholder, product/ticket placeholder panel, and settings placeholder. It does not call IG
directly and it cannot place trades. When connected, selecting a discovered product subscribes to
read-only live quotes and updates the chart header with bid, ask, variation, and percent change.

In the Settings tab:

- Open `Tools > Settings` or the top `Settings` button to configure credentials.
- The settings dialog is a tab widget. Its first tab stores live and demo API identifiers.
- `Apply` or `Save` writes all non-secret settings to the local user config file.
- Passwords and API keys are stored in the OS keyring, never in the JSON config file.
- The top account ribbon has `Connect live`, `Connect demo`, `Settings`, and an account dropdown.
- After a successful read-only connection, the top account ribbon displays only the selected
  account value, available funds, gain/loss, and coverage/deposit.
- For `demo`, use the demo API key and the demo API identifier/password chosen in the IG demo API
  keys page, not the email address of the web account.
- For `live`, use the live API key and matching live API login identifier/password.

## P02 status

- Read-only product discovery service and CLI are available.
- GUI product discovery is available from the `Products / Ticket` panel. It uses the selected
  stored live/demo profile, first tries the IG enabled categories endpoint, then market navigation,
  then conservative read-only market searches. It displays products in a table and can export a
  sanitized JSON report. It does not bulk-fetch details for every EPIC because IG can reject long
  read-only scans with an invalid security token.
- Product discovery results are grouped in GUI tabs by product family and asset class. Bid/offer
  and variation columns are displayed when the IG search payload provides them; true real-time
  updates are not implemented yet. Use `Tradeable only` to hide offline instruments.
- The search fallback uses curated seeds aligned with the current IG tabs, including common crypto
  barrier underlyings such as Bitcoin, Ether, Solana, Chainlink, Polkadot, Uniswap, Avalanche,
  Dogecoin, Litecoin, Ripple, and Stellar.
- The product text field is a local filter on displayed results; it does not change the IG API
  discovery query.
- Product classification is heuristic and conservative.
- GUI shell and chart foundation are available.
- IG streaming is available for selected-product read-only quotes, but no order path exists.
- Real-time chart updates are limited to the live quote header and live price line.
- Ticket execution, trade manager, pending orders, risk automation, macro/news APIs, and database
  persistence are not implemented yet.

## Project layout

The package follows `docs/prd/10_architecture/package_layout.md`. Broker-facing code is isolated
under `src/trading_ig_assistant/adapters/`, UI modules stay thin placeholders, and core/domain
modules remain independent from Qt and IG connectivity.
