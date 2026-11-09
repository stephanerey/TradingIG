import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from trading_ig_assistant.adapters.openai_market_context import (
    OPENAI_RESPONSES_URL,
    OpenAIContextProviderConfig,
    OpenAIContextProviderError,
    OpenAIHttpResponse,
    OpenAIResponsesMarketContextProvider,
)
from trading_ig_assistant.domain.ai_context import AIAnalysisStatus, MarketAIRequest
from trading_ig_assistant.domain.macro_context import ContextSeverity, ContextSignal
from trading_ig_assistant.services.ai_context_service import build_market_context_snapshot
from trading_ig_assistant.services.macro_context_service import MacroContextService

NOW = datetime(2026, 11, 4, 14, 0, tzinfo=UTC)
FAKE_KEY = "test-openai-secret-value"


def _macro_state():
    signal = ContextSignal(
        signal_id="FED-SIGNAL-1",
        label="Federal Reserve context",
        severity=ContextSeverity.YELLOW,
        score=None,
        summary="Official normalized context metadata",
        source="Federal Reserve Board",
        source_url="https://www.federalreserve.gov/example",
        observed_at_utc=NOW - timedelta(minutes=1),
        valid_until_utc=NOW + timedelta(minutes=20),
        confidence=None,
        tags=("central_bank",),
    )
    return MacroContextService().build_state((signal,), NOW)


def _output() -> dict[str, object]:
    return {
        "directional_bias": "unknown",
        "event_risk": "medium",
        "confidence": 0.6,
        "summary": "Insufficient directional evidence; central-bank context requires caution.",
        "risk_flags": ["CENTRAL_BANK_CONTEXT"],
        "source_signal_ids": ["FED-SIGNAL-1"],
    }


def _response(output: object | None = None) -> OpenAIHttpResponse:
    text = json.dumps(_output() if output is None else output)
    return OpenAIHttpResponse(
        body=json.dumps(
            {
                "status": "completed",
                "output": [
                    {"type": "reasoning", "summary": []},
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": text}],
                    },
                ],
            }
        ).encode(),
        final_url=OPENAI_RESPONSES_URL,
        content_type="application/json; charset=utf-8",
    )


def _request() -> MarketAIRequest:
    return MarketAIRequest(
        instrument_id="IX.D.NASDAQ.IFD.IP",
        prompt_version="market-context-v1",
        macro_state=_macro_state(),
        generated_at_utc=NOW,
    )


def test_openai_provider_builds_strict_bounded_request_without_web_or_broker_data() -> None:
    captured: dict[str, object] = {}

    def transport(url, headers, body, timeout, max_bytes):
        captured.update(
            url=url,
            headers=dict(headers),
            body=body,
            timeout=timeout,
            max_bytes=max_bytes,
        )
        return _response()

    provider = OpenAIResponsesMarketContextProvider(
        OpenAIContextProviderConfig(
            model="explicit-model-snapshot",
            api_key=FAKE_KEY,
            max_output_tokens=600,
        ),
        transport=transport,
    )

    output = provider.analyze(_request())

    payload = json.loads(captured["body"])
    supplied_context = json.loads(payload["input"])
    assert output == _output()
    assert provider.model_id == "openai-responses:explicit-model-snapshot"
    assert captured["url"] == OPENAI_RESPONSES_URL
    assert captured["headers"]["Authorization"] == f"Bearer {FAKE_KEY}"
    assert payload["model"] == "explicit-model-snapshot"
    assert payload["store"] is False
    assert payload["max_output_tokens"] == 600
    assert "tools" not in payload
    assert "untrusted data" in payload["instructions"]
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["strict"] is True
    schema = payload["text"]["format"]["schema"]
    assert schema["additionalProperties"] is False
    source_schema = schema["properties"]["source_signal_ids"]
    assert source_schema["items"]["enum"] == ["FED-SIGNAL-1"]
    assert source_schema["minItems"] == 1
    assert source_schema["maxItems"] == 1
    assert supplied_context["instrument_id"] == "IX.D.NASDAQ.IFD.IP"
    assert supplied_context["signals"][0]["eligible_for_citation"] is True
    serialized = captured["body"].decode()
    assert FAKE_KEY not in serialized
    assert "account_id" not in serialized
    assert "ticket" not in serialized.lower()
    assert "order" not in supplied_context


def test_openai_payload_excludes_expired_and_future_signals() -> None:
    from dataclasses import replace

    captured = {}

    def transport(_url, _headers, body, _timeout, _max_bytes):
        captured.update(json.loads(body))
        return _response()

    provider = OpenAIResponsesMarketContextProvider(
        OpenAIContextProviderConfig(model="fixture-model", api_key=FAKE_KEY, max_output_tokens=600),
        transport=transport,
    )
    request = _request()
    active = request.macro_state.signals[0]
    expired = replace(active, signal_id="EXPIRED", valid_until_utc=NOW)
    future = replace(active, signal_id="FUTURE", observed_at_utc=NOW + timedelta(seconds=1))
    request = replace(
        request, macro_state=replace(request.macro_state, signals=(active, expired, future))
    )
    provider.analyze(request)
    supplied = json.loads(captured["input"])
    assert [signal["signal_id"] for signal in supplied["signals"]] == [active.signal_id]


def test_openai_provider_excludes_data_health_from_citation_schema() -> None:
    captured: dict[str, object] = {}
    state = _macro_state()
    health_signal = ContextSignal(
        signal_id="HEALTH-ONLY",
        label="Provider availability",
        severity=ContextSeverity.GREEN,
        score=None,
        summary="Source endpoint is reachable",
        source="runtime",
        source_url=None,
        observed_at_utc=NOW,
        valid_until_utc=NOW + timedelta(minutes=20),
        confidence=None,
        tags=("data_health",),
    )
    request = MarketAIRequest(
        instrument_id="IX.D.NASDAQ.IFD.IP",
        prompt_version="market-context-v1",
        macro_state=MacroContextService().build_state(
            (*state.signals, health_signal),
            NOW,
        ),
        generated_at_utc=NOW,
    )

    def transport(_url, _headers, body, _timeout, _max_bytes):
        captured["body"] = body
        return _response()

    provider = OpenAIResponsesMarketContextProvider(
        OpenAIContextProviderConfig(
            model="explicit-model-snapshot",
            api_key=FAKE_KEY,
            max_output_tokens=600,
        ),
        transport=transport,
    )

    provider.analyze(request)

    payload = json.loads(captured["body"])
    supplied_context = json.loads(payload["input"])
    eligibility = {
        signal["signal_id"]: signal["eligible_for_citation"]
        for signal in supplied_context["signals"]
    }
    source_enum = payload["text"]["format"]["schema"]["properties"]["source_signal_ids"]["items"][
        "enum"
    ]
    assert eligibility == {"FED-SIGNAL-1": True, "HEALTH-ONLY": False}
    assert source_enum == ["FED-SIGNAL-1"]


def test_openai_provider_integrates_with_typed_conservative_service() -> None:
    provider = OpenAIResponsesMarketContextProvider(
        OpenAIContextProviderConfig(
            model="explicit-model-snapshot",
            api_key=FAKE_KEY,
            max_output_tokens=600,
        ),
        transport=lambda *_args: _response(),
    )

    snapshot = build_market_context_snapshot(
        snapshot_id="AI-SNAPSHOT-1",
        instrument_id="IX.D.NASDAQ.IFD.IP",
        macro_state=_macro_state(),
        generated_at_utc=NOW,
        valid_for=timedelta(minutes=15),
        prompt_version="market-context-v1",
        provider=provider,
    )

    assert snapshot.ai_analysis.status is AIAnalysisStatus.AVAILABLE
    assert snapshot.ai_analysis.confidence == Decimal("0.6")
    assert snapshot.ai_analysis.source_signal_ids == ("FED-SIGNAL-1",)
    assert "model:openai-responses:explicit-model-snapshot" in snapshot.provenance


@pytest.mark.parametrize(
    "response",
    (
        OpenAIHttpResponse(
            body=b'{"status":"in_progress","output":[]}',
            final_url=OPENAI_RESPONSES_URL,
            content_type="application/json",
        ),
        OpenAIHttpResponse(
            body=json.dumps(
                {
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "refusal", "refusal": "Cannot comply"}],
                        }
                    ],
                }
            ).encode(),
            final_url=OPENAI_RESPONSES_URL,
            content_type="application/json",
        ),
        OpenAIHttpResponse(
            body=b'{"status":"completed","output":[]}',
            final_url=OPENAI_RESPONSES_URL,
            content_type="application/json",
        ),
        OpenAIHttpResponse(
            body=b"not-json",
            final_url=OPENAI_RESPONSES_URL,
            content_type="application/json",
        ),
        OpenAIHttpResponse(
            body=b"{}",
            final_url="https://example.invalid/responses",
            content_type="application/json",
        ),
    ),
)
def test_openai_response_failures_degrade_to_unavailable(response) -> None:
    provider = OpenAIResponsesMarketContextProvider(
        OpenAIContextProviderConfig(
            model="explicit-model-snapshot",
            api_key=FAKE_KEY,
            max_output_tokens=600,
        ),
        transport=lambda *_args: response,
    )

    snapshot = build_market_context_snapshot(
        snapshot_id="AI-SNAPSHOT-1",
        instrument_id="IX.D.NASDAQ.IFD.IP",
        macro_state=_macro_state(),
        generated_at_utc=NOW,
        valid_for=timedelta(minutes=15),
        prompt_version="market-context-v1",
        provider=provider,
    )

    assert snapshot.ai_analysis.status is AIAnalysisStatus.UNAVAILABLE
    assert snapshot.ai_analysis.confidence is None
    assert snapshot.ai_analysis.source_signal_ids == ()
    assert "AI_PROVIDER_ERROR" in snapshot.reason_codes


def test_openai_provider_rejects_unpinned_endpoint_and_redacts_secret_representation() -> None:
    with pytest.raises(ValueError, match="pinned official"):
        OpenAIContextProviderConfig(
            model="explicit-model-snapshot",
            api_key=FAKE_KEY,
            max_output_tokens=600,
            endpoint="https://example.invalid/responses",
        )

    config = OpenAIContextProviderConfig(
        model="explicit-model-snapshot",
        api_key=FAKE_KEY,
        max_output_tokens=600,
    )
    provider = OpenAIResponsesMarketContextProvider(config, transport=lambda *_args: _response())

    assert FAKE_KEY not in repr(config)
    assert FAKE_KEY not in repr(provider)


def test_openai_provider_enforces_request_and_response_limits() -> None:
    provider = OpenAIResponsesMarketContextProvider(
        OpenAIContextProviderConfig(
            model="explicit-model-snapshot",
            api_key=FAKE_KEY,
            max_output_tokens=600,
            max_request_bytes=10,
        ),
        transport=lambda *_args: _response(),
    )
    with pytest.raises(OpenAIContextProviderError, match="request exceeds"):
        provider.analyze(_request())

    oversized = OpenAIHttpResponse(
        body=b"x" * 101,
        final_url=OPENAI_RESPONSES_URL,
        content_type="application/json",
    )
    provider = OpenAIResponsesMarketContextProvider(
        OpenAIContextProviderConfig(
            model="explicit-model-snapshot",
            api_key=FAKE_KEY,
            max_output_tokens=600,
            max_response_bytes=100,
        ),
        transport=lambda *_args: oversized,
    )
    with pytest.raises(OpenAIContextProviderError, match="size limit"):
        provider.analyze(_request())


def test_live_probe_refuses_to_run_without_environment_secret() -> None:
    environment = dict(os.environ)
    environment.pop("OPENAI_API_KEY", None)
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_openai_context_probe.py",
            "--model",
            "explicit-model-snapshot",
            "--max-output-tokens",
            "600",
            "--acknowledge-cost-and-metadata-transmission",
        ],
        cwd=os.fspath(Path(__file__).resolve().parents[2]),
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "OPENAI_API_KEY must be set" in result.stderr
