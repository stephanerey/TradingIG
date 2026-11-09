# API001 — IG REST Adapter

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Original text is preserved; documented V1.2 changes govern current scope. No implementation or activation is implied.


> **PRD Policy:** **PROJECT (editable)** — Feature specification.\
**Last updated:** 2026-10-22


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

## V1.2 scope alignment

Historical signatures are illustrative, not proof of actual IG support. Require AccountRef and per-product/account capabilities. ANALYSIS forbids submit/update/close; ambiguous responses require reconciliation. Real HTTP payloads and error codes must be evidenced during R07, not invented here.

Canonical requirements: [chapter 4](../10_architecture/overview.md), [chapter 5](F001_ig_connection_and_settings.md), [chapter 9](F007_software_pending_orders.md), [chapter 17](../10_architecture/domain_contracts.md).
