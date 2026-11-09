# 11 — Modèles de projection et contrats de données GUI

## Doctrine

Les pages reçoivent des **snapshots typés, immuables et datés** des services existants. Elles n'invoquent pas directement IG, OpenAI, SQLite ou le RiskEngine. Les appels opérationnels passent par des **commandes applicatives** contrôlées. `view-model` ≠ source de vérité. Aucune boucle Qt ne doit effectuer un appel HTTP bloquant.

## A. Contrat de lecture (exemple Python, sans migration de langage)

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

class Availability(StrEnum):
    READY = "ready"
    WARMING_UP = "warming_up"
    STALE = "stale"
    DATA_GAP = "data_gap"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"

@dataclass(frozen=True)
class DataProvenance:
    source: str
    observed_at_utc: datetime | None
    received_at_utc: datetime | None
    scope: str
    availability: Availability
    reason_codes: tuple[str, ...] = ()

@dataclass(frozen=True)
class Amount:
    value: Decimal | None
    currency: str
    provenance: DataProvenance
    estimate: bool = False

@dataclass(frozen=True)
class AccountHeaderVM:
    account_id: str | None
    ig_environment: str | None
    product_account_type: str | None
    execution_mode: str
    equity: Amount | None
    available_funds: Amount | None
    day_pnl: Amount | None
    week_pnl: Amount | None
    month_pnl: Amount | None
    open_positions_count: int | None
    ig_rest_status: str
    ig_stream_status: str
    ai_status: str
    generated_at_utc: datetime
```

Ces classes sont **exemples de contrats cible** : Codex doit confirmer les modèles du dépôt, réutiliser le domaine existant et implémenter les conversions dans des services de projection. Ne pas introduire un second modèle autonome de compte si `domain.instruments.Account` et `domain.adapter_contracts.AccountRef` suffisent.

## B. Autres modèles cibles

`MarketRowVM`: `underlying_id`, display name, last_quote, variation, per-component score + band/reasons, AI scope/status, upcoming_event, risk, decision, last_scanned_at, availability.  
`ProductRowVM`: `product_epic`, `bound_underlying_id?`, product type, exposure direction, order capability, bid/ask, spread, fees/KO/expiry/size/currency, provenance.  
`PositionRowVM`: account+environment+position ID (clé composite), Paper/Broker, price/age, PnL and status, stop proposed/confirmed, KO, TP, state, permissions/capabilities, audit link.  
`PnlSeriesVM`: account scope, Paper/Broker, granularity (DAY/WEEK/MONTH/YEAR), currency, per-bucket pnl realized/net/estimated, opening equity, ending equity, missing flags, methodology label, provenance.  
`MarketAnalysisVM`: `underlying_id`, technical/timeframe readiness, strategy outputs, macro snapshot, AI snapshot with `model_id`, `prompt_version`, `valid_until`, validated bindings and confidence; source-specific unknowns.  
`HealthServiceVM`: service, status, last_success_at, last_error_at, latency, quota, age, reason and available probe.  
`OptimizationProposalVM`: proposal ID, scope, old/new params, hypothesis, dataset fingerprint, replay evidence, confidence/limits, approval state, created_at, version.

## C. Calculs / garanties des projections

- Clés stables par `(environment, account_id, product_epic, position_id)` ; ne jamais mélanger DEMO/LIVE ou Paper/IG.
- `DataProvenance` source+UTC+quality; `unknown` n'est jamais converti en `0` pour score/solde/PnL.
- Les données expirées gardent leur date d'origine, avec `STALE` et requêtes interrompues selon contrat.
- Un calcul de PnL dans la GUI est interdit : employer `AnalyticsProjectionService` et la logique d'événements/FX validée.
- Les derniers prix de produits différents et les historiques de référence ne sont **pas** interchangeables.
- `Error` et `Loading` sont des états en première classe, pas du texte générique sans cause.

## D. Bus de snapshots / commandes

```text
IG REST / Lightstreamer ─┐
PaperSession / SQLite ────┼──> Application services / cache cohérent
Scanner / Macro / OpenAI ─┘               │
                                         v
                               UI read models / projections
                                         │
                          Qt signal (queued, coalesced)
                                         │
                                         v
                         Page controllers / QAbstractTableModels
                                         │
                      Intentions explicites utilisateur
                                         v
                       Application command facade
                              │             │
                       RiskEngine     Permissions / capabilities
                              │             │
                              └──────┬──────┘
                                     v
                              Paper ONLY (GUI V2)
```

L'illustration n'introduit aucun chemin d'exécution broker LIVE. Un `OpenAIHealthModel` n'est **pas** une session connectée permanente.

## E. Performance / cycle de vie

- Une seule source d'abonnement streaming pour l'application, par combinaison environnement/compte/EPIC, avec références/release propres.
- Diffusion UI bornée (p.ex. 2-4 Hz pour lignes de cotation, 1 Hz bandeau PnL, mise à jour graphique coalescée), sans ralentir les calculs métier ou perdre la date de la dernière observation.
- Workers/threads via signaux Qt `QueuedConnection`, annulation et générations de requêtes; les résultats d'une ancienne session de compte ne doivent jamais repeupler la nouvelle.
- Verrouillage limité aux états partagés ; les modèles `QAbstractTableModel` ne se modifient que dans le thread GUI; le core reste testable hors Qt.
- Pas de persistance de secrets ni de payload brut non expurgé dans les tableaux ou les exports.

## Exigences

- **GUI2-DATA-001** : snapshots GUI immuables, provenance, timestamp, scope et status.
- **GUI2-DATA-002** : projections financières centralisées et unités/devise sûres.
- **GUI2-DATA-003** : un seul runtime/connecteur/flux, pas d'appels cachés en UI.
- **GUI2-DATA-004** : états inconnus, périmés, non applicables, données manquantes conservés jusqu'à l'UI.
- **GUI2-DATA-005** : émission Qt thread-safe, coalescing et sélection par IDs stables.
- **GUI2-DATA-006** : séparation analyses/consultation des commandes transactionnelles.
- **GUI2-DATA-007** : migration backward-compatible des états/config, absence de perte de journal.
