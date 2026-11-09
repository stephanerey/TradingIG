"""Run one manually requested OpenAI analysis over normalized market context."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.adapters.openai_market_context import (
    OpenAIContextProviderConfig,
    OpenAIResponsesMarketContextProvider,
)
from trading_ig_assistant.domain.ai_context import MarketContextSnapshot
from trading_ig_assistant.domain.macro_context import MacroRibbonState
from trading_ig_assistant.services.ai_context_service import build_market_context_snapshot


def run_openai_market_context(
    *,
    model: str,
    api_key: SecretValue,
    max_output_tokens: int,
    macro_state: MacroRibbonState,
    instrument_id: str,
    now: datetime | None = None,
) -> MarketContextSnapshot:
    """Execute one bounded consultative call; this service has no broker dependency."""

    generated_at = now or datetime.now(UTC)
    provider = OpenAIResponsesMarketContextProvider(
        OpenAIContextProviderConfig(
            model=model,
            api_key=api_key,
            max_output_tokens=max_output_tokens,
        )
    )
    return build_market_context_snapshot(
        snapshot_id=f"OPENAI-CONTEXT-{uuid4()}",
        instrument_id=instrument_id,
        macro_state=macro_state,
        generated_at_utc=generated_at,
        valid_for=timedelta(minutes=10),
        prompt_version="openai-market-context-v1",
        provider=provider,
    )
