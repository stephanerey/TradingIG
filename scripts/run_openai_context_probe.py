"""Run one explicitly authorized, metadata-only OpenAI context validation request."""

from __future__ import annotations

import argparse
import json
import os

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.domain.ai_context import AIAnalysisStatus
from trading_ig_assistant.services.openai_context_probe_service import (
    run_openai_context_probe,
)

ACKNOWLEDGEMENT_FLAG = "--acknowledge-cost-and-metadata-transmission"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Send one synthetic normalized market-context request to OpenAI. "
            "No IG account, credential, ticket or order data is included."
        )
    )
    parser.add_argument("--model", required=True, help="Exact OpenAI model or snapshot ID")
    parser.add_argument(
        "--max-output-tokens",
        required=True,
        type=int,
        help="Explicit output-token cap (1..2000)",
    )
    parser.add_argument(
        ACKNOWLEDGEMENT_FLAG,
        action="store_true",
        help="Acknowledge API cost and normalized metadata transmission",
    )
    args = parser.parse_args()
    if not args.acknowledge_cost_and_metadata_transmission:
        parser.error(f"{ACKNOWLEDGEMENT_FLAG} is required for a live request")

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        parser.error("OPENAI_API_KEY must be set in the current process environment")

    snapshot = run_openai_context_probe(
        model=args.model,
        api_key=SecretValue(api_key),
        max_output_tokens=args.max_output_tokens,
    )
    analysis = snapshot.ai_analysis
    print(
        json.dumps(
            {
                "status": analysis.status.value,
                "model_id": analysis.model_id,
                "directional_bias": analysis.directional_bias.value,
                "event_risk": analysis.event_risk.value,
                "confidence": str(analysis.confidence) if analysis.confidence is not None else None,
                "source_signal_ids": list(analysis.source_signal_ids),
                "reason_codes": list(snapshot.reason_codes),
            },
            indent=2,
        )
    )
    return 0 if analysis.status is AIAnalysisStatus.AVAILABLE else 2


if __name__ == "__main__":
    raise SystemExit(main())
