# F006 — Ticket Builder and Risk Engine

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Earlier project text is preserved; explicit V1.2 changes take precedence only on documented conflicts. This is not implementation or activation evidence.


> **PRD Policy:** **PROJECT (editable)** — Feature specification.\
**Last updated:** 2026-10-22


## Goal
Generate a complete IG ticket proposal and validate it against strict risk rules.

## Non-goals
- The ticket builder does not decide the trade alone; it consumes setup/product/risk inputs.

## Requirements
- Include the current `MacroRibbonState` snapshot in ticket validation and warnings. Red/high event-risk status should require explicit confirmation or apply configured risk reduction.
- Inputs: account capital, selected product, direction, entry/current price, KO/barrier level, stop distance/level, limit distance/level, desired risk, min/max size, fees/prime/cost where available.
- Outputs: quantity, stop, limit, expected loss, expected gain, R/R ratio, R value, KO distance, warnings, rejection reasons.
- Enforce max risk per trade.
- Enforce max exposure across open positions.
- Reject tickets with invalid KO distance, poor R/R, stale data, unsupported product, or excessive size.
- Support long and short calculations.

## Constraints
- All calculations must be deterministic and unit-tested.
- No UI widget may bypass risk validation.

## Acceptance criteria
- Given known examples, engine computes the same expected stop loss and target gain as manual calculation.
- Oversized quantities are rejected.
- User override is possible only with explicit warning and journal event, not silently.

## Testing notes
- Unit-test numerical calculations with tolerance.
- Test edge cases: min size, currency conversion, zero/negative stop distance, stale quotes.

## Partial implementation evidence — 2026-10-23

The Paper ticket supports a provisional relative-entry mode with default stop/target distances
`4/12` and an explicit absolute-price alternative. These defaults are sized to remain below the
initial 10 EUR risk budget for the standard equity 1,000 EUR, size 1 and typical narrow spread;
they are a Paper validation example, not a market recommendation. Relative BUY and SELL inputs are resolved
deterministically from the simulated executable entry and the absolute levels are displayed before
submission. Barrier KO remains an independent absolute level. Its initial 9 EUR maximum-loss value
is visibly treated as a Paper assumption requiring review, not a broker-certified amount. This UI translation does not bypass
the existing risk, FX, freshness, KO or R/R vetoes and cannot call an IG order method.

An advisory `READY` analysis directive may now feed the same deterministic Paper ticket builder,
but only through a strict handoff which verifies directive expiry, exact Scanner/product identity
and entry-zone compatibility. The handoff exposes the matching `RiskRequest`; it never treats the
analysis score as a risk approval and never evaluates, reserves or submits the intent. All existing
Risk Engine vetoes therefore remain mandatory.

The proposal can also be reviewed through the non-reserving `RiskEngine.evaluate` boundary. The
immutable result retains `APPROVED`/`REJECTED`, rejection reasons, budget/loss values and resolved
setting sources. Approval is explicitly not a reservation, Paper authorization or execution;
intent expiry is checked before review and an operator action is still required.

The explicit local Paper action now rechecks expiry and calls the atomic risk reservation path on
the current portfolio snapshot before delegating to the existing idempotent `PaperBroker` flow.
The exact fill assumptions and reviewed settings are retained. Missing confirmation, a rejected
review or newly occupied exposure prevents submission. No runtime invokes this action
automatically and it cannot route to IG.

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 8; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-8"></a>

## 8. Moteur de risque et dimensionnement

### 8.1 Définitions et invariants

Définir `E_ref_day` = equity de référence au début de la journée configurée (horodatage/currency explicites) ; `E_current` = equity courante fiable ; `E_basis` = `min(E_ref_day, E_current)` par défaut. Le budget par trade est `B_trade = E_basis × 0,01` par défaut. Le seuil de perte journalière est `L_day = E_ref_day × 0,03`. L'interface doit permettre d'ajuster pourcentage, devise de référence, période, règles d'exposition et seuils **dans des bornes sûres**.

**Important :** pour un CFD sans stop garanti, aucune borne de perte absolue ne peut être déduite d'un simple stop logiciel. Les limites représentent des seuils de décision avec scénarios d'écart/gap, non une garantie contractuelle.

**REQ-RISK-001/P0** Vérifier les limites **par compte, globales et par sous-jacent** sur toutes les positions ouvertes, pending réservés et ouvertures en cours. Le contrôle doit être atomique au regard des ordres concurrents.\
**REQ-RISK-002/P0** Refuser une ouverture si sa perte **au stop estimée nette**, majorée des coûts et du slippage de scénario, dépasse le budget. Pour les barrières, afficher et contrôler séparément le **risque maximum jusqu'au KO/premium** ; politique initiale conservatrice : rejet si perte maximale au KO dépasse également le budget alloué.\
**REQ-RISK-003/P0** Si le minimum négociable, le pas de taille, la conversion FX ou les caractéristiques du contrat empêchent de respecter la limite, proposer `NO_TRADE`, pas un dépassement implicite.\
**REQ-RISK-004/P0** Plafonds initiaux `max_open_global=1` et `max_open_per_underlying=1` (paramétrables) ; le système doit compter aussi les intentions d'ouverture en état in-flight pour éviter les doubles déclenchements.\
**REQ-RISK-005/P0** Lorsqu'une perte quotidienne nette (réalisée + latente, sans double comptage) atteint 3 % du `E_ref_day`, interdire toute **nouvelle ouverture** ; la surveillance, réduction ou clôture de risque restent permises. Afficher compte/marché/devise et état.\
**REQ-RISK-006/P0** Distinguer explicitement trois grandeurs non interchangeables : risque financier calculé par le moteur, niveau de risque de marché estimé (technique et IA), confiance/calibration du modèle IA. Aucune « corrélation » naïve de deux nombres sans méthodologie documentée.\
**REQ-RISK-007/P0** Rejeter compte incertain, données de prix obsolètes, marché fermé, produit non supporté, KO invalide, R/R inférieur au seuil choisi, taille non valide, ordre doublon ou exposition inconnue critique.\
**REQ-RISK-008/P1** Exposition corrélée : classer instruments selon sous-jacent et groupes de risque (indices actions, matières premières, etc.) ; seuil configurable et avertissements/veto selon politique.\
**REQ-RISK-009/P1** Calculer bid/ask réel, taille, marge/premium, commissions, financement probable, conversion FX et impact spread ; distinguer estimations et montants confirmés.\
**REQ-RISK-010/P1** Paramètres risk GUI : valeur, unité, plage valide, héritage global→compte→stratégie→marché, changements audités. Les garde-fous critiques ne peuvent pas être contournés par IA, script ou UI.\
**REQ-RISK-011/P1** Afficher avant validation le risque en euros, en %, scénario au stop, au KO, stress-gap, profit net potentiel et R/R.

### 8.2 Calculs d'exemple et tests

Pour un marché coté en points, avec valeur du point `V` par unité de taille, taille `Q`, coût total anticipé `C` et distance stop `D`, la perte estimée est `Q × V × D + C` **uniquement si** la convention de prix du produit, la devise et le mode d'exécution rendent cette formule applicable. Les options/barrières nécessitent leur formule de contrat validée ; aucune conversion « points sous-jacent = prime barrière » n'est autorisée.

**AC-RISK-001** Un capital de référence de 1 000 EUR produit un budget nominal de 10 EUR à 1 %, avant particularités du produit et des frais.\
**AC-RISK-002** Une position et une intention pending réservée épuisent le plafond global 1 ; la seconde ouverture concurrente est rejetée.\
**AC-RISK-003** Une perte nette journalière de 30 EUR sur equity début de journée de 1 000 EUR bloque les nouvelles entrées et laisse la clôture ouverte.\
**AC-RISK-004** L'IA donne score « faible risque » mais FX ou spread indisponible : le ticket est refusé malgré le score.\
**AC-RISK-005** Deux positions sur le même sous-jacent via CFD et barrière consomment le même plafond de marché.

## V1.2 traceability

[Chapter 4](../10_architecture/overview.md) · [Chapter 9](F007_software_pending_orders.md) · [Acceptance matrix](../90_quality/acceptance_matrix.md) · [Definition of Done](../90_quality/definition_of_done.md). Criteria are specifications, not passed test results.
