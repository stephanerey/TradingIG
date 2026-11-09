# Decisions

- Use the Responses API with strict `text.format` JSON Schema, as documented by OpenAI.
- Set `store` to `false` and send only normalized context/provenance, never IG credentials,
  account data, ticket data or broker state.
- Require a caller-supplied model ID and API key; no model, budget or billing assumption is made.
- Do not enable built-in web search in this lot because retrieved sources are not yet normalized
  into the application's source-lineage contract.
- Reject refusal, incomplete status, ambiguous/multiple output texts and invalid JSON.
