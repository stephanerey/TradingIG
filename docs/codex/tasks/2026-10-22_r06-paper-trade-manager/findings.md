# Findings

- `domain/pending_orders.py`, `domain/tickets.py`, `domain/trade_state.py`, `domain/positions.py`, `services/pending_order_engine.py`, `services/ticket_builder.py` and `services/trade_manager.py` are placeholders.
- `domain/adapter_contracts.py` already defines `OrderIntent`, `ExecutionResult` and a `BrokerAdapter` contract suitable for a separate paper implementation.
- The existing IG REST order methods remain hard-blocked by `LiveTradingDisabledError` and have regression coverage.
- R03 risk, R04 journal and R05 macro/scanner contracts can be consumed without adding a live execution route.
- Fill assumptions must be explicit configuration/fixture inputs; no claim of live realism is justified from OHLC-only data.
- `PaperBroker` satisfies the provider-neutral broker protocol but advertises DEMO/LIVE as unsupported and accepts only `paper/paper` account scope.
- Software pending orders expose the explicit warning that app-managed protection stops when the application stops.
- Trade and pending transitions are represented as append-only `JournalEvent` records; no runtime database is created automatically.
- Local alerts have cooldown and acknowledgement but no external delivery in R06.
