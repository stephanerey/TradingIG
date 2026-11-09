"""Build one synthetic, validation-only OpenAI market-context probe."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.adapters.openai_market_context import (
    OpenAIContextProviderConfig,
    OpenAIResponsesMarketContextProvider,
)
from trading_ig_assistant.domain.ai_context import MarketContextSnapshot
from trading_ig_assistant.domain.macro_context import ContextSeverity, ContextSignal
from trading_ig_assistant.services.ai_context_service import build_market_context_snapshot
from trading_ig_assistant.services.macro_context_service import MacroContextService


def run_openai_context_probe(
    *,
    model: str,
    api_key: SecretValue,
    max_output_tokens: int,
    now: datetime | None = None,
) -> MarketContextSnapshot:
    """Send one bounded synthetic request; no IG or user-market data is included."""

    generated_at = now or datetime.now(UTC)
    signal = ContextSignal(
        signal_id="OPENAI-PROBE-OFFICIAL-CONTEXT",
        label="OpenAI provider validation context",
        severity=ContextSeverity.YELLOW,
        score=None,
        summary=(
            "Synthetic validation evidence only; no directional market conclusion is supplied."
        ),
        source="TradingIG validation fixture",
        source_url="https://developers.openai.com/api/docs/guides/structured-outputs",
        observed_at_utc=generated_at,
        valid_until_utc=generated_at + timedelta(minutes=15),
        confidence=None,
        tags=("validation_only", "central_bank"),
    )
    macro_state = MacroContextService().build_state((signal,), generated_at)
    provider = OpenAIResponsesMarketContextProvider(
        OpenAIContextProviderConfig(
            model=model,
            api_key=api_key,
            max_output_tokens=max_output_tokens,
        )
    )
    return build_market_context_snapshot(
        snapshot_id=f"OPENAI-PROBE-{uuid4()}",
        instrument_id="VALIDATION-ONLY",
        macro_state=macro_state,
        generated_at_utc=generated_at,
        valid_for=timedelta(minutes=10),
        prompt_version="openai-context-probe-v1",
        provider=provider,
    )
