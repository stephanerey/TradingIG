# F008 — Trade Monitor and Dynamic Stop Manager

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Earlier project text is preserved; explicit V1.2 changes take precedence only on documented conflicts. This is not implementation or activation evidence.


> **PRD Policy:** **PROJECT (editable)** — Feature specification.\
**Last updated:** 2026-10-22


## Goal
Monitor open trades and manage stop updates using deterministic R-based state-machine rules.

## Non-goals
- No discretionary stop changes by hidden logic.
- No widening stop after entry.

## Requirements
- Trade states: `OPEN`, `PROTECTED`, `TRAILING`, `CLOSING`, `CLOSED`.
- Calculate initial risk `R` from entry and initial stop.
- At configured threshold, move stop to break-even + costs if supported or recommend this action.
- At later thresholds, trail stop by one of configurable modes:
  - fixed R lock-in;
  - recent candle lows/highs;
  - ATR/volatility;
  - manual level.
- Never move a long stop downward or a short stop upward.
- Allow limit to remain fixed by default.
- Optional future mode: raise limit in strict stages when trend accelerates.
- Log every recommendation/update and user override.

## Constraints
- Must handle barriers where KO liquidation differs from normal stop behavior.
- Must account for API order-update support and fall back to manual recommendation if unsupported.
- Must not over-tighten every tick; use candle closes, cooldown, and minimum step.

## Acceptance criteria
- Given a simulated trade path, stop updates match expected state transitions.
- Stop cannot be widened through the trade manager.
- User can see why a stop update is recommended.

## Testing notes
- Unit-test long and short state machines.
- Replay the example workflow: +1R → stop to break-even; further gain → trail/secure.

## Partial implementation evidence — 2026-10-23

The volatile GUI Paper session exposes an explicit stop-tightening action and a manual local close
for the selected open Paper position. The existing Paper boundary rejects widening, records
confirmed changes and now records rejected action reasons in the session journal. These controls
cannot call an IG adapter and do not claim broker stop-update support, persistent recovery or the
complete automatic trailing workflow.

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 10; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-10"></a>

## 10. Trade Manager et sécurisation

**REQ-TRADE-001/P1** États `OPEN` → `PROTECTED` → `TRAILING` → `CLOSING` → `CLOSED`, avec transitions monotones et historique.\
**REQ-TRADE-002/P1** Fonction « Sécuriser » : lorsqu'un profit latent franchit un seuil configurable (défaut +1R), proposer ou demander un stop dont le **P&L net théorique à ce niveau** est ≥0, avec coussin configurable ; niveaux calculés selon sens long/short et spécifications du produit.\
**REQ-TRADE-003/P1** Distinguer *break-even du prix*, *break-even net après spread/commissions* et *profit protégé*. Un stop non garanti n'assure pas la réalisation du P&L affiché en cas de gap ou slippage.\
**REQ-TRADE-004/P1** Modes trailing configurables : distance fixe, multiples R, ATR, lows/highs de bougies clôturées, manuel ; pas de resserrement sur chaque tick sans seuil/cooldown.\
**REQ-TRADE-005/P1** Par défaut, **ne jamais élargir** le stop : pour LONG `new_stop >= confirmed_stop`; pour SHORT `new_stop <= confirmed_stop`, sauf procédure manuelle exceptionnelle distincte, explicitement désactivée dans l'automate.\
**REQ-TRADE-006/P1** Un stop n'est déclaré « sécurisé » qu'après confirmation du broker, pas à l'envoi de la requête. Si API ne permet pas la modification, afficher instruction/alerte manuelle.\
**REQ-TRADE-007/P1** Paramétrer gestion du take profit, clôture temporelle, seuil de retournement et prise partielle uniquement pour produits qui la supportent.\
**REQ-TRADE-008/P1** Chaque suggestion/modification indique motif, contexte, frais retenus, ancien niveau, nouveau niveau et confirmation/rejet courtier.\
**REQ-TRADE-009/P1** L'automate conserve les protections en cours en cas de blocage de nouvelles entrées ; réconcilie les niveaux après reconnexion.

**AC-TRADE-001** Une position LONG dont le stop initial est 100 ne peut pas recevoir 99 comme modification automatique.\
**AC-TRADE-002** L'utilisateur voit le P&L net théorique protégé et la mention non garantie.\
**AC-TRADE-003** Un refus API ne produit pas l'état `PROTECTED`.\
**AC-TRADE-004** Une nouvelle quote défavorable n'inverse pas un stop déjà confirmé.

## V1.2 traceability

[Chapter 4](../10_architecture/overview.md) · [Acceptance matrix](../90_quality/acceptance_matrix.md) · [Definition of Done](../90_quality/definition_of_done.md). Criteria are specifications, not passed test results.
