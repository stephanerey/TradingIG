import json

import pytest

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.adapters.openai_market_context import (
    OPENAI_RESPONSES_URL,
    OpenAIContextProviderError,
    OpenAIHttpResponse,
)
from trading_ig_assistant.services.openai_web_research import WebResearchError, research_market


def _response(*, citations=True, searched=True):
    annotations = [
        {"type": "url_citation", "title": "Banque centrale", "url": "https://example.org/news"}
    ]
    output = [
        {"type": "web_search_call", "status": "completed"},
        {
            "type": "message",
            "content": [
                {
                    "type": "output_text",
                    "text": "Synthèse",
                    "annotations": annotations if citations else [],
                }
            ],
        },
    ]
    if not searched:
        output.pop(0)
    return OpenAIHttpResponse(
        json.dumps({"status": "completed", "output": output}).encode(),
        OPENAI_RESPONSES_URL,
        "application/json",
    )


def test_research_requires_web_and_returns_actual_citations():
    captured = {}

    def transport(url, headers, body, timeout, limit):
        captured.update(json.loads(body))
        return _response()

    result = research_market(
        market="France 40", model="test", api_key=SecretValue("secret"), transport=transport
    )
    assert result.summary == "Synthèse"
    assert result.sources == (("https://example.org/news", "Banque centrale"),)
    assert captured["tools"][0]["type"] == "web_search"
    assert captured["tool_choice"] == "required"
    assert captured["store"] is False
    assert captured["max_output_tokens"] == 6000
    assert "secret" not in json.dumps(captured)


@pytest.mark.parametrize("citations,searched", [(False, True), (True, False)])
def test_research_without_citations_or_completed_search_is_unavailable(citations, searched):
    with pytest.raises(OpenAIContextProviderError):
        research_market(
            market="France 40",
            model="test",
            api_key=SecretValue("secret"),
            transport=lambda *_: _response(citations=citations, searched=searched),
        )


def test_incomplete_token_limit_has_safe_specific_diagnostic():
    response = OpenAIHttpResponse(
        json.dumps(
            {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}
        ).encode(),
        OPENAI_RESPONSES_URL,
        "application/json",
    )
    with pytest.raises(WebResearchError) as exc:
        research_market(
            market="France 40",
            model="gpt-6-luna",
            api_key=SecretValue("secret"),
            transport=lambda *_: response,
        )
    assert exc.value.code == "OUTPUT_LIMIT"
    assert "secret" not in str(exc.value)


def test_gpt6_search_uses_bounded_reasoning():
    captured = {}

    def transport(_url, _headers, body, *_):
        captured.update(json.loads(body))
        return _response()

    research_market(
        market="France 40", model="gpt-6-luna", api_key=SecretValue("secret"), transport=transport
    )
    assert captured["reasoning"] == {"effort": "low"}
