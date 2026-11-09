# Scanner runtime batch

## Objective

Connect the existing exact product bindings and session-only candle router to the broker-independent
multi-market Scanner when the operator explicitly refreshes the provisional Scanner tab.

## Boundaries

- Exact configured product bindings only; no name or EPIC-pattern inference.
- Closed session candles only; warmup, missing products and rejected streams remain explicit.
- Manual refresh only; no periodic scheduling, ticket, broker, order or AUTO path.
- Keep the provisional single-product rendering until the dedicated GUI redesign.

## Skills

- `codex-tradingig-analysis-scanner`

