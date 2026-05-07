# API001 — IG REST Adapter

> **PRD Policy:** **PROJECT (editable)** — Feature specification.  
**Last updated:** 2026-05-07


## Goal
Encapsulate all IG REST API interactions behind a testable adapter.

## Non-goals
- Do not expose raw HTTP details to UI or business services.
- Do not implement live order execution before P00/P20 validation and explicit gating.

## Responsibilities
- Authenticate and manage REST session tokens.
- Retrieve accounts and selected account status.
- Search markets and retrieve market details/snapshots.
- Retrieve historical prices/candles.
- Retrieve open positions and activity/history.
- Create/update/close positions if enabled and supported.
- Retrieve/create/update/delete working orders if enabled and supported for the target product.
- Normalize IG errors.

## Candidate methods
```python
class IGRestAdapter:
    def login(self, credentials: IGCredentials) -> IGSession: ...
    def logout(self) -> None: ...
    def get_accounts(self) -> list[Account]: ...
    def switch_account(self, account_id: str) -> None: ...
    def search_markets(self, query: str) -> list[MarketSummary]: ...
    def get_market_details(self, epic: str) -> MarketDetails: ...
    def get_historical_prices(self, epic: str, resolution: str, start, end) -> list[Candle]: ...
    def get_open_positions(self) -> list[Position]: ...
    def create_otc_position(self, ticket: BrokerTicket) -> DealResult: ...
    def update_position(self, deal_id: str, update: PositionUpdate) -> DealResult: ...
    def close_position(self, deal_id: str, close: CloseRequest) -> DealResult: ...
    def get_working_orders(self) -> list[WorkingOrder]: ...
```

## Constraints
- Headers/tokens must be redacted from logs.
- Adapter must expose capabilities per product/account when possible.
- All methods must have timeout handling.

## Acceptance criteria
- Mocked unit tests cover success, rejection, session expiry, market closed, unsupported product.
- Demo login and read-only calls work in integration test.

## Testing notes
- Use HTTP response fixtures with fake tokens.
- Integration tests opt-in via environment flag.
