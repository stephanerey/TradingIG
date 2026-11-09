# Findings

- The existing `MarketAIProvider` contract and `build_market_context_snapshot` already validate an
  exact output shape, active cited signals, model/prompt/time/confidence provenance and conservative
  fallback.
- Official OpenAI documentation recommends Responses API for new text generation and Structured
  Outputs rather than JSON mode where supported.
- Responses may contain several output items; raw REST parsing must inspect all message content
  rather than assuming `output[0].content[0]`.
- A first real request would transmit normalized market-context metadata and incur API usage, so it
  remains a human validation gate.
