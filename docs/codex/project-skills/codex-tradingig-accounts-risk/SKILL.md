---
name: codex-tradingig-accounts-risk
description: >-
  Apply TradingIG account-isolation and conservative portfolio-risk rules when changing account state, risk settings, ticket validation, exposure reservations or related tests. Use it to preserve deterministic vetoes, explicit provenance and the analysis-only broker boundary defined by the reconstructed V1.2 PRD.
---

# TradingIG accounts and risk

Read `references/rules.md` before changing account or risk behavior.

## Non-negotiable boundary

- Keep broker execution disabled unless a later, separately authorized phase proves and activates it.
- Never allow UI, scripts, technical scores or AI commentary to override a financial veto.
- Do not invent configurable bounds or product formulas absent from authoritative sources.
- Use synthetic account IDs and values in tests and evidence.

## Required closure

- Verify account scope and broker-confirmed account switching.
- Cover missing FX/exposure, 1%/3% defaults, global/underlying limits and concurrent reservations.
- Run the protected-order regression alongside targeted and full tests.
