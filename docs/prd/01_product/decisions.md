# Decisions

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](decisions.md) apply. Earlier project text is preserved; explicit V1.2 changes take precedence only on documented conflicts. This is not implementation or activation evidence.


> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-10-22

Use this as an ADR-light log.

## Decisions
- **ID:** D-001
  - **Date:** 2026-05-07
  - **Context:** The product can become dangerous if it tries to trade autonomously before API support and risk controls are proven.
  - **Decision:** MVP is a disciplined assistant with manual confirmation by default. Fully automatic live execution is out of MVP scope.
  - **Alternatives:** Full robot from day one; rejected because API/product constraints and risk-management logic are not yet verified.
  - **Consequences:** Build adapters and state machines now, but gate live order execution behind explicit settings and tests.

- **ID:** D-002
  - **Date:** 2026-05-07
  - **Context:** IG Barriers/Options may not support native delayed orders in the same way the user wants to trade them from the platform.
  - **Decision:** Implement software pending orders: the app monitors trigger conditions and alerts/prepares the user to place/confirm the ticket manually.
  - **Alternatives:** Only use IG native working orders; rejected until product support is proven for the target products.
  - **Consequences:** Need robust trigger states, validation, expiry, cooldown, and logging.

- **ID:** D-003
  - **Date:** 2026-05-07
  - **Context:** Credentials will be entered through a configuration screen.
  - **Decision:** Credentials MUST be stored in OS keyring or equivalent encrypted storage, not plaintext config files.
  - **Alternatives:** `.env` or YAML config with password/API key; rejected for live account safety.
  - **Consequences:** Implement a credential provider abstraction and redaction tests.

- **ID:** D-004
  - **Date:** 2026-05-07
  - **Context:** The user wants a chart close to IG visual workflow.
  - **Decision:** The app will implement an IG-like candlestick chart with trading overlays, not a generic line chart.
  - **Alternatives:** rely only on IG web UI; rejected because software pending order and stop management need integrated overlays.
  - **Consequences:** Chart model and UI must support candle aggregation, overlay layers, and real-time updates.

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 2; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-2"></a>

## 2. Décisions fermes et valeurs par défaut

| ID | Décision validée | Valeur initiale / règle |
|---|---|---|
| ADR-001 | Application **Windows uniquement** | Python 3.12 cible à qualifier, PyQt5/PyQtGraph ; GUI ouverte en fonctionnement permanent |
| ADR-002 | Trois modes de trading | `ANALYSIS`, `SUPERVISED`, `AUTO`; démarrage en `ANALYSIS` |
| ADR-003 | IG premier broker, architecture extensible | `BrokerAdapter`, `MarketDataProvider` découplés |
| ADR-004 | Deux types de comptes IG | CFD et Barrières/Options, capables d'être suivis ensemble ; capacités par produit à vérifier |
| ADR-005 | Marchés initiaux | Gold Spot, US Tech 100, France 40, pétrole ; Germany 40 disponible/configurable |
| ADR-006 | Stratégies | Trend, breakout, pullback, événements ; indicateurs et sentiment configurables |
| ADR-007 | Durée des trades | Minutes à heures ; M1/M5/M15, contexte H1/H4 |
| ADR-008 | Risque maximal par trade | **1 %** par défaut, paramétrable par compte ; voir règles conservatrices §8 |
| ADR-009 | Perte/jour | **3 %** de l'equity de référence du début de journée ; blocage des nouvelles ouvertures |
| ADR-010 | Positions simultanées | **1 globale et 1 par sous-jacent** au défaut, deux contraintes indépendantes |
| ADR-011 | Break-even / sécurisation | Déclenchement proposé à **+1R** ; objectif net après coûts ; seuils paramétrables |
| ADR-012 | Scanner | Score explicable par stratégie et consensus ; poids, filtres et classement configurables |
| ADR-013 | IA | Analyse/recommandation d'abord ; proposition/exécution automatique ensuite, seulement avec contrôles |
| ADR-014 | GUI | Dock/panneaux et tabs, layout persisté, paramètres accessibles GUI |
| ADR-015 | Notifications | Windows + e-mail + Telegram ; activation, catégories et fréquence configurables |
| ADR-016 | Données | Cache historique d'abord, backfill ciblé, streaming, imports fichiers |
| ADR-017 | Données TradingView | Pas de dépendance obligatoire à un abonnement TradingView |
| ADR-018 | Travaux existants | Conserver la branche avancée et refactorer incrémentalement |

Les valeurs ci-dessus sont des **valeurs par défaut, pas des cibles de performance**. Les seuils dérogeant aux garde-fous essentiels imposent une validation visible et un événement d'audit ; certaines contraintes ne sont jamais contournables (compte ambigu, ordre dupliqué, donnée critique périmée, API non prise en charge).

## Reconciliation decisions — 2026-10-22

D-001–D-004 remain recorded. These decisions implement the approved reconstruction.

| ID | Conflict | Resolution |
|---|---|---|
| D-005 | Original V1.2 unavailable | Label the delivery V1.2 reconstructed; archive V1.1 and map all chapters/requirements. Do not claim identity with the missing pack. |
| D-006 | P00 bootstrap versus existing application | Preserve Pxx history and unverified TODOs. Current work is documentation only; next eligible task is SR00 preview. Chapter 18 SR00/R00–R08 supersedes the older roadmap in the archived audit. |
| D-007 | English templates and French source | Use this project-specific conventions extension. Preserve locked templates and original English; retain French source wording. |
| D-008 | Manual MVP versus future AUTO/replay | Preserve D-001 for the initial supervised delivery. Paper validation is R06/P1; quantitative replay remains P2. R07 requires demo/capability evidence and supervised gates; R08 automation is optional. This consolidation authorizes no real execution. |
| D-009 | Broad historical risk overrides | REQ-RISK-001–011 prevail: no override of uncertain account/exposure, stale critical data, unsupported capability, duplicate order or financial veto. Permitted parameter changes remain explicit and audited. |
| D-010 | Older states and REST-first flow | Chapter 9 defines canonical execution/pending states; chapter 10 adds CLOSING and broker-confirmed protection; chapter 6 requires cache-first data. Preserve old labels for migration analysis; CONFIRMED/EXECUTED do not imply broker confirmation without evidence. Future migration requires compatibility tests. |
| D-011 | Preliminary platforms/schemas/APIs | Target Windows 11, PyQt5/PyQtGraph and Python 3.12 to qualify. Preserve current packaging requiring >=3.11. Old SQL/signature sketches are preliminary; chapters 4/6/13/17 define target contracts. No schema migration or API capability is inferred. |
| D-012 | SR 4.1 and fixed branches in source prompts | SR 4.1 remains a target pending verified SR00. Current AGENTS.md, task memories and branch remain. Archived instructions are not executed by consolidation. |
| D-013 | REQ-RISK-010 versus REQ-UI-005 settings precedence | Human decision on 2026-10-22: `global -> account -> strategy -> market`; later layers override earlier layers and the selected origin remains inspectable. |
| D-014 | Stable selectors for persisted Scanner profile layers | Human decision on 2026-11-05: account patches use the IG account ID, strategy patches use `StrategyId`, and market patches use a canonical underlying rather than an expiring Barrier/Option EPIC. Product-to-canonical mapping must be explicit, not inferred silently. |
| D-015 | Initial canonical Scanner underlying vocabulary | Human decision on 2026-11-05: use the stable codes `US_TECH_100`, `FRANCE_40`, `GERMANY_40`, `SPOT_GOLD`, and `US_CRUDE`. Free-form aliases and IG EPICs are not canonical IDs. |

## Resolved settings conflict

The original conflict is preserved in its source requirements and resolved by D-013 for implementation. Risk parameter bounds beyond the conservative defaults, capability support and concrete schema migration still require design/evidence.
