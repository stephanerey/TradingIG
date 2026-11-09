# Task plan — R05 OpenAI context provider

## Objective

Implement a concrete, optional OpenAI Responses API adapter for the existing typed market-context
boundary, with strict structured output and no live call before human authorization.

## Smallest sufficient approach

1. Require an injected secret and an explicit model identifier; choose no default model.
2. Serialize only normalized macro-context signals and their provenance.
3. Request strict JSON Schema output from the Responses API with storage disabled.
4. Parse all output items safely, reject refusals/incomplete/malformed responses and let the
   existing service degrade them to `UNAVAILABLE/UNKNOWN`.
5. Use an injected transport for complete offline request/response/security tests.
6. Stop before a paid network call or runtime activation.

## Scope

Allowed: stdlib HTTPS adapter, explicit endpoint allowlist, redacted secret, strict schema,
offline tests and focused documentation.

Forbidden: live API request, model/cost selection, web-search tool, key persistence, GUI activation,
headline truth claims, scanner score change, ticket, Paper/DEMO/LIVE/AUTO execution.

## Skills

- `openai-docs`
- `codex-tradingig-analysis-scanner`
