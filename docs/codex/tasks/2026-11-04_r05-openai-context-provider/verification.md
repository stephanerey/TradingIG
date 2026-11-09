# Verification

## Official guidance

- Responses API request/header and multi-item output shape verified against official OpenAI text
  generation documentation.
- Strict `text.format` JSON Schema, refusal handling and `additionalProperties: false` constraints
  verified against official OpenAI Structured Outputs documentation.

## Offline evidence

- Final targeted OpenAI/AI/protected-order tests: `33 passed in 0.30s`.
- Full suite: `310 passed in 14.27s`.
- Targeted Ruff lint and format: passed.
- Requests use the pinned official endpoint, `store: false`, no tools, a caller-selected model and
  an injected redacted secret. Payload assertions exclude account, ticket and order state.
- Refusal, incomplete response, empty/ambiguous output, invalid JSON, redirect and size violations
  all degrade through the typed service to `UNAVAILABLE/UNKNOWN`.
- The one-shot probe refuses to run without both an explicit acknowledgement and
  `OPENAI_API_KEY`; model and output-token cap are required command-line values.

## Human gate

No OpenAI request was sent. A model, secure API key, budget and permission to transmit normalized
market-context metadata must be approved before one bounded live validation request.
