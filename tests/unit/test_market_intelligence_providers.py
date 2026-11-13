import json
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest

from trading_ig_assistant.adapters.api_connection_testers import GdeltConnectionTester
from trading_ig_assistant.adapters.gdelt_news import (
    GdeltHttpResponse,
    GdeltNewsError,
    GdeltNewsProvider,
)
from trading_ig_assistant.adapters.tavily_extract import (
    TAVILY_EXTRACT_URL,
    TavilyExtractConfig,
    TavilyExtractHttpResponse,
    TavilyExtractProvider,
)
from trading_ig_assistant.adapters.tavily_news import (
    TAVILY_SEARCH_URL,
    TavilyHttpResponse,
    TavilyNewsConfig,
    TavilyNewsError,
    TavilyNewsProvider,
)
from trading_ig_assistant.domain.api_credentials import (
    API_PROVIDER_BY_ID,
    ApiProviderStatus,
)
from trading_ig_assistant.domain.context_sources import ContextCategory
from trading_ig_assistant.domain.market_intelligence import (
    IntelligenceProviderKind,
    NewsSearchRequest,
    PublicationTimeStatus,
    VerificationStatus,
)

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)


def test_tavily_uses_basic_news_metadata_contract_and_exact_usage() -> None:
    captured: dict[str, object] = {}

    def transport(url, headers, body, timeout, max_bytes):
        captured.update(
            url=url,
            headers=headers,
            body=json.loads(body),
            timeout=timeout,
            max_bytes=max_bytes,
        )
        payload = {
            "results": [
                {
                    "id": "article-1",
                    "title": "Fed signals patience",
                    "url": "https://news.example/fed",
                    "published_date": "Wed, 11 Nov 2026 08:30:00 GMT",
                    "content": "This snippet must not enter the normalized record.",
                    "raw_content": "forbidden body",
                    "score": 0.87,
                }
            ],
            "usage": {"credits": 1},
            "request_id": "request-1",
        }
        return TavilyHttpResponse(
            json.dumps(payload).encode(),
            TAVILY_SEARCH_URL,
            "application/json; charset=utf-8",
        )

    provider = TavilyNewsProvider(TavilyNewsConfig(api_key="secret-key"), transport=transport)
    request = NewsSearchRequest(
        "Federal Reserve policy",
        ContextCategory.CENTRAL_BANK,
        recent_window=timedelta(hours=6),
    )

    result = provider.search_news(request, as_of_utc=NOW)

    assert captured["url"] == TAVILY_SEARCH_URL
    assert captured["headers"]["Authorization"] == "Bearer secret-key"
    body = captured["body"]
    assert body["topic"] == "news"
    assert body["search_depth"] == "basic"
    assert body["max_results"] == 10
    assert body["start_date"] == "2026-11-11"
    assert body["end_date"] == "2026-11-12"
    assert body["filter_by_published_date"] is False
    assert "max_age_hours" not in body
    assert body["include_answer"] is False
    assert body["include_raw_content"] is False
    assert body["include_published_date"] is True
    assert body["include_usage"] is True
    assert result.provider_kind is IntelligenceProviderKind.TAVILY
    assert result.usage.credits == 1
    assert result.records[0].publication_time_status is PublicationTimeStatus.PROVIDER_ESTIMATE
    assert result.records[0].verification_status is VerificationStatus.SINGLE_SOURCE
    assert result.records[0].news.summary is None
    assert result.records[0].search_excerpt == (
        "This snippet must not enter the normalized record."
    )
    assert "forbidden body" not in repr(result.records[0])
    assert "secret-key" not in repr(provider._config)


def test_tavily_marks_missing_publication_time_unknown_and_rejects_missing_usage() -> None:
    def response(payload):
        return TavilyHttpResponse(
            json.dumps(payload).encode(),
            TAVILY_SEARCH_URL,
            "application/json",
        )

    provider = TavilyNewsProvider(
        TavilyNewsConfig(api_key="secret"),
        transport=lambda *_args: response(
            {
                "results": [
                    {"title": "Unknown publication", "url": "https://news.example/unknown"}
                ],
                "usage": {"credits": 1},
            }
        ),
    )
    request = NewsSearchRequest("macro", ContextCategory.OTHER)
    result = provider.search_news(request, as_of_utc=NOW)
    record = result.records[0]
    assert record.publication_time_status is PublicationTimeStatus.UNKNOWN
    assert record.news.published_at_utc == NOW

    invalid = TavilyNewsProvider(
        TavilyNewsConfig(api_key="secret"),
        transport=lambda *_args: response({"results": []}),
    )
    with pytest.raises(TavilyNewsError, match="credit usage"):
        invalid.search_news(request, as_of_utc=NOW)


def test_tavily_extract_basic_accepts_partial_results_and_accounts_exact_usage() -> None:
    captured: dict[str, object] = {}

    def transport(url, headers, body, timeout, max_bytes):
        captured.update(url=url, headers=headers, body=json.loads(body))
        return TavilyExtractHttpResponse(
            json.dumps(
                {
                    "results": [
                        {
                            "url": "https://news.example/one",
                            "raw_content": "Useful extracted article content.",
                        }
                    ],
                    "failed_results": [{"url": "https://news.example/two"}],
                    "usage": {"credits": 1},
                    "request_id": "extract-1",
                }
            ).encode(),
            TAVILY_EXTRACT_URL,
            "application/json",
        )

    provider = TavilyExtractProvider(
        TavilyExtractConfig(api_key="secret"), transport=transport
    )
    result = provider.extract(
        ("https://news.example/one", "https://news.example/two"),
        query="market impact",
    )

    assert captured["body"]["extract_depth"] == "basic"
    assert captured["body"]["urls"] == [
        "https://news.example/one",
        "https://news.example/two",
    ]
    assert result.articles[0].content == "Useful extracted article content."
    assert result.failed_urls == ("https://news.example/two",)
    assert result.usage.credits == 1


def test_tavily_extract_marks_empty_or_unavailable_content_failed() -> None:
    provider = TavilyExtractProvider(
        TavilyExtractConfig(api_key="secret"),
        transport=lambda *_args: TavilyExtractHttpResponse(
            b'{"results":[{"url":"https://news.example/empty","raw_content":"  "}],'
            b'"usage":{"credits":0}}',
            TAVILY_EXTRACT_URL,
            "application/json",
        ),
    )

    result = provider.extract(("https://news.example/empty",))

    assert result.articles == ()
    assert result.failed_urls == ("https://news.example/empty",)
    assert result.usage.credits == 0


def test_tavily_rejects_provider_results_outside_the_requested_time_window() -> None:
    payload = {
        "results": [
            {
                "id": "recent",
                "title": "Recent market update",
                "url": "https://news.example/recent",
                "published_date": "Wed, 11 Nov 2026 08:30:00 GMT",
            },
            {
                "id": "stale",
                "title": "Old market update",
                "url": "https://news.example/stale",
                "published_date": "Tue, 10 Nov 2026 01:00:00 GMT",
            },
        ],
        "usage": {"credits": 1},
    }
    provider = TavilyNewsProvider(
        TavilyNewsConfig(api_key="secret"),
        transport=lambda *_args: TavilyHttpResponse(
            json.dumps(payload).encode(),
            TAVILY_SEARCH_URL,
            "application/json",
        ),
    )

    result = provider.search_news(
        NewsSearchRequest(
            "markets",
            ContextCategory.OTHER,
            recent_window=timedelta(hours=6),
        ),
        as_of_utc=NOW,
    )

    assert tuple(record.news.headline for record in result.records) == (
        "Recent market update",
    )


def test_gdelt_uses_doc_article_json_and_keeps_discoveries_unconfirmed() -> None:
    captured: dict[str, object] = {}

    def transport(url, headers, timeout, max_bytes):
        captured.update(url=url, headers=headers, timeout=timeout, max_bytes=max_bytes)
        payload = {
            "articles": [
                {
                    "url": "https://wire.example/sanctions",
                    "title": "Government announces new sanctions",
                    "seendate": "20261111T084500Z",
                    "domain": "wire.example",
                    "tone": -9.5,
                }
            ]
        }
        return GdeltHttpResponse(
            json.dumps(payload).encode(),
            url,
            "application/json",
        )

    provider = GdeltNewsProvider(transport=transport)
    request = NewsSearchRequest(
        "sanctions OR conflict",
        ContextCategory.GEOPOLITICAL,
        max_results=7,
        recent_window=timedelta(hours=2),
    )

    result = provider.search_news(request, as_of_utc=NOW)

    query = parse_qs(urlsplit(captured["url"]).query)
    assert query["mode"] == ["ArtList"]
    assert query["format"] == ["json"]
    assert query["maxrecords"] == ["7"]
    assert query["timespan"] == ["120min"]
    record = result.records[0]
    assert record.provider_kind is IntelligenceProviderKind.GDELT
    assert record.verification_status is VerificationStatus.UNCONFIRMED
    assert record.news.importance.value == "unknown"
    assert all("buy" not in tag and "sell" not in tag for tag in record.news.tags)


def test_provider_contracts_reject_redirects_and_non_utc_observations() -> None:
    request = NewsSearchRequest("macro", ContextCategory.OTHER)
    tavily = TavilyNewsProvider(
        TavilyNewsConfig(api_key="secret"),
        transport=lambda *_args: TavilyHttpResponse(
            b'{"results": [], "usage": {"credits": 1}}',
            "https://redirect.example/",
            "application/json",
        ),
    )
    with pytest.raises(TavilyNewsError, match="redirected"):
        tavily.search_news(request, as_of_utc=NOW)

    gdelt = GdeltNewsProvider(
        transport=lambda url, *_args: GdeltHttpResponse(
            b'{"articles": []}',
            f"{url}&redirected=yes",
            "application/json",
        )
    )
    with pytest.raises(GdeltNewsError, match="redirected"):
        gdelt.search_news(request, as_of_utc=NOW)
    with pytest.raises(ValueError, match="UTC"):
        gdelt.search_news(request, as_of_utc=NOW.replace(tzinfo=None))


def test_gdelt_connection_test_reports_public_rate_limit_without_key_error(
    monkeypatch,
) -> None:
    def rate_limited(*_args, **_kwargs):
        raise GdeltNewsError(
            "GDELT HTTP request failed",
            reason_code="GDELT_RATE_LIMITED",
        )

    monkeypatch.setattr(GdeltNewsProvider, "search_news", rate_limited)

    result = GdeltConnectionTester()(API_PROVIDER_BY_ID["gdelt"], None)

    assert result.status is ApiProviderStatus.QUOTA_EXHAUSTED
    assert result.reason_code == "GDELT_RATE_LIMITED"
