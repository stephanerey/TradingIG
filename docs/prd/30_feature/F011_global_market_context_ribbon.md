# F011 — Global Market Context Ribbon

> **PRD Policy:** **PROJECT (editable)** — Feature specification.  
**Last updated:** 2026-05-07

## Goal
Add a compact, always-visible market context ribbon directly below the main menu / top toolbar. The ribbon summarizes global market drivers with red/yellow/green status indicators so the user can immediately see whether the current macro/news environment supports, weakens, or warns against a trade idea.

This ribbon is the visible UI output of `MacroContextService` and complements, but does not replace, the technical scanner and risk engine.

## Placement in the UI
The main window layout MUST reserve a horizontal control band in this order:

```text
[Main menu / app toolbar]
[Global Market Context Ribbon]
[Workspace tabs / instrument tabs]
[Chart + ticket + monitor panels]
```

The ribbon should remain visible while switching instruments, chart timeframes, product contracts, or open position views.

## Visual design
Each context item is shown as a small tile/pill with:
- short label;
- traffic-light status: `GREEN`, `YELLOW`, `RED`, `GRAY`;
- compact score or bias text;
- last update / freshness marker;
- optional icon;
- tooltip with details, source and timestamp;
- click action opening a detailed context panel.

Color semantics:
- `GREEN`: supportive / low-risk / aligned with the considered trade direction;
- `YELLOW`: mixed, uncertain, elevated caution, or upcoming event;
- `RED`: high risk, adverse context, stale critical feed, or strong event risk;
- `GRAY`: unavailable, disabled provider, or insufficient data.

The UI MUST NOT rely only on color. Each tile also needs text/icon state for accessibility and screenshots.

## Initial ribbon indicators
MVP should include a configurable subset of these indicators:

| Indicator | Example labels | Purpose |
|---|---|---|
| Market regime | `Risk-on`, `Neutral`, `Risk-off` | Global bias for equity-index trades |
| Fed / FOMC | `FOMC today`, `Fed quiet`, `Speech soon` | US rate-event risk |
| Macro releases | `CPI soon`, `NFP passed`, `PMI mixed` | Scheduled high-impact calendar risk |
| US yields | `Yields ↑`, `Yields flat`, `Yields ↓` | Pressure/support for US Tech and gold |
| USD | `USD strong`, `USD weak`, `USD mixed` | Context for gold and global indices |
| Oil / energy | `Oil spike`, `Oil calm` | Geopolitical/inflation stress proxy |
| Volatility | `VIX high`, `VIX falling`, `Vol calm` | Risk appetite / gap-risk proxy |
| Geopolitical risk | `High`, `Elevated`, `Calm` | Headline-driven market warning |
| Gold context | `Gold supported`, `Gold pressured`, `Gold neutral` | Specific bias context for Spot Gold |
| Data health | `Live`, `Stale`, `Provider down` | Warn if the analysis is not reliable |

## Aggregate state
The left side of the ribbon should show an aggregate market state:

```text
GLOBAL CONTEXT: Risk-on / Neutral / Risk-off
Index bias: Bullish / Neutral / Bearish
Gold bias: Bullish / Neutral / Bearish
Event risk: Low / Medium / High
```

This aggregate MUST be derived from individual `ContextSignal` values and persisted in the journal when a ticket is generated.

## Domain model
Add domain models equivalent to:

```python
class ContextSeverity(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    GRAY = "gray"

@dataclass(frozen=True)
class ContextSignal:
    id: str
    label: str
    severity: ContextSeverity
    score: float | None          # normalized, e.g. -100..+100
    summary: str
    source: str
    source_url: str | None
    observed_at_utc: datetime
    valid_until_utc: datetime | None
    confidence: float | None     # 0..1 when available
    tags: tuple[str, ...]

@dataclass(frozen=True)
class MacroRibbonState:
    regime: str                  # risk_on, neutral, risk_off, unknown
    index_bias: str              # bullish, neutral, bearish, unknown
    gold_bias: str
    event_risk: str              # low, medium, high, unknown
    signals: tuple[ContextSignal, ...]
    generated_at_utc: datetime
```

## Interaction with other modules
- `MacroContextService` computes `MacroRibbonState`.
- `Market Dashboard / Scanner` displays the same macro flags next to technical setup scores.
- `TicketBuilder` receives the current `MacroRibbonState` and may add warnings such as `HIGH_EVENT_RISK`.
- `RiskEngine` may require extra user confirmation or reduce recommended size when `event_risk == high`.
- `SoftwarePendingOrderEngine` must re-check the ribbon state at trigger time, not only when the pending order was armed.
- `JournalService` stores a compact snapshot of the ribbon state for every generated ticket and executed trade.

## Configuration
The Settings UI should allow:
- enabling/disabling each indicator tile;
- choosing refresh intervals per provider;
- setting event-risk lookahead windows, e.g. 15 min / 30 min / 60 min before high-impact news;
- selecting whether red macro status blocks trade generation, only warns, or requires explicit override;
- selecting data providers for economic calendar/news/market proxies.

## Non-goals
- The ribbon is not an autonomous trading signal.
- It must not display long copyrighted article content.
- It must not make investment-advice claims such as guaranteed direction.
- It must not block manual user decisions without a visible override path, except when data/account safety checks fail.

## Acceptance criteria
- Ribbon is visible below the menu bar in the main trading workspace.
- Each enabled indicator has a status color, label, summary tooltip, source, timestamp and freshness status.
- A stale or failed provider turns the affected indicator `GRAY` or `RED` depending on severity.
- Ticket generation records the current ribbon state in the journal.
- Scanner and ticket builder can consume macro flags produced by the ribbon state.
- Unit tests cover aggregate regime computation from mocked signals.
- UI tests or screenshots verify that the ribbon remains visible while switching instruments.

## Testing notes
- Use mocked provider adapters for deterministic states: all-green risk-on, mixed/yellow, red event-risk, stale data.
- Test that high-impact scheduled events inside the configured lookahead window raise at least `YELLOW`, and `RED` if configured as hard warning.
- Test that a software pending order revalidates macro status at trigger time.
