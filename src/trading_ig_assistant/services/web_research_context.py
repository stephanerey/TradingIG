"""Turn a cited web research digest into a short-lived, consultative AI context."""

from __future__ import annotations

import hashlib
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
from trading_ig_assistant.services.openai_web_research import WebResearchResult


def analyze_web_research(
    result: WebResearchResult,
    *,
    instrument_id: str,
    api_key: SecretValue,
    now: datetime | None = None,
    provider=None,
) -> MarketContextSnapshot:
    """Treat the generated digest as one secondary source, not independent raw articles."""
    if not result.sources or not result.summary.strip() or not instrument_id.strip():
        raise ValueError("Cited research and a product are required")
    generated_at = now or datetime.now(UTC)
    source_urls = "\n".join(url for url, _ in result.sources[:20])
    identifier = hashlib.sha256(
        (instrument_id + result.summary + source_urls).encode("utf-8")
    ).hexdigest()[:20]
    signal = ContextSignal(
        signal_id=f"web-research:{identifier}",
        label="Synthèse IA de recherche web avec liens cités",
        severity=ContextSeverity.GRAY,
        score=None,
        summary=(
            "Synthèse secondaire générée par IA, non vérifiée indépendamment. "
            "Les liens cités sont consultables dans la recherche ; ne pas supposer que "
            "chaque source confirme chaque affirmation.\n"
            + result.summary[:12000]
            + "\nLiens cités :\n"
            + source_urls
        ),
        source="OpenAI web research",
        source_url=None,
        observed_at_utc=generated_at,
        valid_until_utc=generated_at + timedelta(minutes=10),
        confidence=None,
        tags=("ai_evidence", "web_research_digest"),
    )
    state = MacroContextService().build_state((signal,), generated_at)
    if provider is None:
        provider = OpenAIResponsesMarketContextProvider(
            OpenAIContextProviderConfig(model=result.model, api_key=api_key, max_output_tokens=2000)
        )
    return build_market_context_snapshot(
        snapshot_id=f"OPENAI-WEB-{uuid4()}",
        instrument_id=instrument_id,
        macro_state=state,
        generated_at_utc=generated_at,
        valid_for=timedelta(minutes=10),
        prompt_version="openai-web-research-v1",
        provider=provider,
    )
