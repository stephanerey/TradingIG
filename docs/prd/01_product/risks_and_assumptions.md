# Risks and Assumptions

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](decisions.md) apply. Earlier project text is preserved; explicit V1.2 changes take precedence only on documented conflicts. This is not implementation or activation evidence.


> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-10-22

## Assumptions
- A1: IG demo access can be enabled with the same email as the live account and a generated API key.
- A2: IG REST and Streaming APIs provide enough market/account data to reconstruct the target workflow.
- A3: Some Barrier/Option operations may not support all order workflows exposed in the web UI; the app must detect support and fall back to manual assisted mode.
- A4: The user will initially run the app locally on a trusted desktop machine.
- A5: The MVP should first be validated in demo mode or dry-run mode before any live execution.

## Risks
| Risk | Impact | Likelihood | Mitigation | Owner |
|---|---|---|---|---|
| R-01 | IG API does not expose all Barrier/Option product data needed | High | Medium | P00 API spike; support read-only/manual workflow if needed | Dev |
| R-02 | IG rejects order/update requests due to market/product constraints | High | Medium | Validate market status, min size, distance rules, API error handling; never assume execution | Dev |
| R-03 | Credentials leaked through config/logs | Critical | Low/Medium | OS keyring, masking, redaction tests, no plaintext secrets | Dev |
| R-04 | Streaming feed disconnects or becomes stale | High | Medium | Heartbeat, stale-data warnings, REST fallback snapshot, disable trading actions while stale | Dev |
| R-05 | Software pending order triggers on a spike or wick | Medium | Medium | Confirmation rules: close-of-candle, hold time, tolerance, cooldown | Dev |
| R-06 | User overtrades after a win | Medium | High | Exposure rules, daily trade limit, warning after winning trade, journal prompt | Product |
| R-07 | News/macro module produces misleading context | Medium | Medium | Source attribution, confidence tags, no automatic trade solely from news | Product/Dev |
| R-08 | Live mode causes financial loss due to bug or latency | Critical | Medium | Demo-first, dry-run, manual confirmation, kill switch, max-loss guard | Product/Dev |

## Open questions
- Q1: Which exact IG EPICs represent the preferred Barrier/Option products for US Tech 100, France 40, Germany 40, and Spot Gold?
- Q2: Does the IG API support listing and opening the same Barrier/Option contracts visible in the web platform for the user account jurisdiction?
- Q3: Can `/workingorders` be used for the target products, or must delayed entry remain software/manual assisted?
- Q4: Which news/economic calendar provider will be used first: IG calendar, public RSS/API, paid provider, or manual event import?
- Q5: Should live mode initially be restricted to manual confirmation only even if API execution is technically possible?

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 20; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-20"></a>

## 20. Risques ouverts, limites externes et jalons bloquants

1. **IG Barrières/Options :** disponibilité réelle de la découverte KO, ouverture, modification stop et clôture selon pays, environnement et compte ; exiger un spike documenté de requêtes/réponses **expurgées** avant R07.
2. **Sessions IG multi-comptes :** déterminer contraintes REST et streaming, changement de contexte atomique, concurrence et comportements de tokens ; tests en démo.
3. **Historique / quotas :** l'allocation et les limites API peuvent évoluer ; ne pas coder une constante immuable. Vérifier sur le compte réel sans multiplier les requêtes.
4. **Fournisseur de news/sentiment :** coûts, licences, horodatages, qualité, politique de conservation et capacité de replay ; choix d'adaptateur et fournisseur configurable.
5. **Précision du risque d'une barrière :** règles de KO, prime, taille, slippage, frais et financement validées sur paramètres broker ; bloquer si prix/contrat insuffisamment décrits.
6. **Qualité des backtests intraday :** des OHLC M1 sans vraie granularité d'exécution peuvent masquer le chemin intra-bougie ; marquer le résultat comme approximation.
7. **Exposition dépendance réseau :** une gestion logicielle de stop/ordre pending ne remplace pas une protection effectivement acceptée par le broker.
8. **Utilisation IA :** sentiment directionnel ≠ probabilité de hausse vérifiée ; score de confiance déclaré ≠ calibration ; l'automatisation exige une comparaison empirique.

**Les points 1, 2 et 5 sont bloquants pour exécuter des Barrières/Options IG en mode réel, pas pour coder les composants abstraits, le Risk Engine ou le mode paper.**

## Consolidation open questions — 2026-10-22

- REQ-RISK-010 and REQ-UI-005 disagree on strategy/market configuration inheritance. D-013 resolves implementation precedence as `global -> account -> strategy -> market`; both original requirements remain preserved for traceability.
- Real broker capabilities, explicit safe parameter bounds and precision/schema choices still need evidence/design review. No capability, test or migration is certified by this PRD.
- SR 4.1 release metadata and installer behavior must be checked against the official source during a separately authorized SR00 task. No method installation is implied by this reconstruction.
