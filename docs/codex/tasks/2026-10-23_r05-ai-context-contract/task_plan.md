# Task plan — R05 AI context contract

## Objective

Implement the missing typed and versioned market-context snapshot plus an interchangeable AI
analysis boundary with explicit safe fallback.

## Authority and limits

- Authorized by the user's validation of the corrected PRD sequence.
- Offline domain/service code and synthetic providers only.
- No external model/provider, network call, dependency, credential, copyrighted article, strategy
  selection, ticket, Paper fill, broker call, AUTO activation, persistence, migration or GUI wiring.
- AI context supplements deterministic indicators; it does not calculate broker truth or override
  risk vetoes.

## Selected project skill

- `codex-tradingig-analysis-scanner`

## Approach

1. Define immutable AI analysis and `MarketContextSnapshot` contracts.
2. Define a provider-neutral protocol returning JSON-like structured data.
3. Strictly validate bias, event risk, confidence, source IDs and allowed fields.
4. Produce explicit unavailable fallback on missing provider, exception or invalid output.
5. Preserve model, prompt, source, timestamp, validity and reason-code provenance.

## Verification

- Valid structured response and snapshot provenance.
- Missing-provider, exception and malformed-output fallback.
- Unknown/extra fields, invalid confidence and unreferenced sources rejected into fallback.
- UTC, expiry and identity contract tests.
- Existing macro/scanner and protected IG regressions plus full offline suite.

## Stop condition

Stop after the offline typed AI context boundary. Do not choose or connect a real model/provider,
generate technical indicators from an LLM, recommend an order or change execution behavior.
