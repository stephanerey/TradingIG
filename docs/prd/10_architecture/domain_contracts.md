# Domain and Adapter Contracts

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstructed from the recovered V1.1.

**Last updated:** 2026-10-22

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 17; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-17"></a>

## 17. Contrats d'API/domaines à fournir à Codex

Le code suivant constitue **un contrat conceptuel** : il décrit responsabilités, paramètres et erreurs, sans imposer le nom définitif de chaque classe ni une implémentation prête à coller. Codex doit compléter `Protocol`, Pydantic/dataclasses si retenu, tests de contrat et erreurs normalisées.

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Protocol, Sequence

class TradingMode(str, Enum):
    ANALYSIS = "analysis"
    SUPERVISED = "supervised"
    AUTO = "auto"

@dataclass(frozen=True)
class AccountRef:
    broker_id: str
    environment: str          # demo / live / paper
    account_id: str

@dataclass(frozen=True)
class BrokerCapabilities:
    read_positions: bool
    place_orders: bool
    modify_stops: bool
    close_positions: bool
    native_pending_orders: bool
    barrier_knockouts: bool

@dataclass(frozen=True)
class OrderIntent:
    intent_id: str
    account: AccountRef
    product_id: str
    underlying_id: str
    direction: str            # BUY / SELL
    quantity: Decimal
    requested_stop: Decimal | None
    requested_target: Decimal | None
    requested_ko: Decimal | None
    signal_id: str | None
    expires_at_utc: datetime

class BrokerAdapter(Protocol):
    def capabilities(self, account: AccountRef, product_id: str) -> BrokerCapabilities: ...
    def accounts(self) -> Sequence[AccountRef]: ...
    def positions(self, account: AccountRef) -> Sequence[object]: ...
    def submit(self, intent: OrderIntent) -> object: ...
    def reconcile(self, account: AccountRef, intent_id: str) -> object: ...
    def move_stop(self, account: AccountRef, position_id: str, stop: Decimal) -> object: ...
    def close(self, account: AccountRef, position_id: str) -> object: ...

class MarketDataProvider(Protocol):
    def history(self, instrument_id: str, timeframe: str, count: int) -> Sequence[object]: ...
    def subscribe(self, instrument_ids: Sequence[str], sink: object) -> object: ...
    def status(self) -> object: ...

class RiskEngine(Protocol):
    def evaluate(self, intent: OrderIntent, snapshot: object) -> object: ...

class Strategy(Protocol):
    def evaluate(self, snapshot: object) -> Sequence[object]: ...
```

Les méthodes `submit/move_stop/close` doivent être indisponibles côté adaptateur réel en mode `ANALYSIS` et tant que l'activation sécurisée n'a pas réussi. Le contrat d'exécution réel doit inclure les champs broker nécessaires et des identifiants corrélables ; en l'absence d'idempotency-key native côté IG, seule la réconciliation empêche une resoumission aveugle.

### 17.1 Format minimal d'événement

```json
{
  "schema_version": 1,
  "event_id": "uuid",
  "correlation_id": "uuid",
  "causation_id": "uuid-or-null",
  "timestamp_utc": "2026-10-20T18:00:00Z",
  "event_type": "ORDER_RISK_REJECTED",
  "broker_id": "ig",
  "environment": "demo",
  "account_ref": "opaque-account-ref",
  "instrument_id": "GOLD_SPOT",
  "intent_id": "uuid",
  "strategy_id": "TREND_FOLLOW",
  "reasons": ["DAILY_RISK_LIMIT", "STALE_QUOTE"],
  "payload": {"estimated_loss_eur": "12.00", "limit_eur": "10.00"}
}
```

*L'exemple est synthétique ; il ne correspond à aucune transaction réelle.* L'event store doit référencer des comptes par identifiants internes/pseudonymes pour les exports.

### 17.2 Exemple de profil de configuration **sans secrets**

```yaml
schema_version: 1
runtime:
  platform: windows
  start_mode: analysis
  keep_gui_open: true
market_data:
  primary_provider: ig
  history_policy: cache_then_bounded_backfill
  chart_timeframe: 5m
  context_timeframes: [15m, 1h]
risk:
  per_trade_pct: 1.0
  daily_drawdown_pct: 3.0
  max_open_global: 1
  max_open_per_underlying: 1
  min_reward_risk_ratio: 2.0
trade_manager:
  break_even_trigger_r: 1.0
  secure_net_profit_buffer: 0.0
  trailing_enabled: false
scanner:
  weights:
    technical: 30
    sentiment: 15
    potential_rr: 20
    market_risk: 15
    execution_cost: 10
    data_quality: 10
  thresholds: {candidate: 75, watch: 60}
notifications:
  windows: true
  email: false
  telegram: false
```

Le GUI peut persister en JSON plutôt qu'en YAML pour compatibilité avec la configuration existante ; l'exigence porte sur la sémantique, le versionnement et la validation, pas sur l'extension du fichier.

## Goal

Define conceptual broker/data/risk/strategy and event/configuration contracts.

## Non-goals

No production endpoint implementation or schema migration.

## Constraints

Account identity, capabilities and execution gates remain explicit; examples contain synthetic values only.

## Acceptance criteria

Contract tests must cover account isolation, unsupported capabilities and ambiguous execution results.

## Testing notes

Future fake-adapter tests and sanitized payload validation; no current capability certification.
