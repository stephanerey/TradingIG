"""Bounded Tavily Extract Basic adapter for transient article evidence."""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.domain.market_intelligence import ProviderUsage

TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"


class TavilyExtractError(RuntimeError):
    def __init__(self, message: str, *, reason_code: str = "TAVILY_EXTRACT_ERROR") -> None:
        super().__init__(message)
        self.reason_code = reason_code


@dataclass(frozen=True)
class TavilyExtractHttpResponse:
    body: bytes
    final_url: str
    content_type: str


ExtractTransport = Callable[
    [str, Mapping[str, str], bytes, float, int], TavilyExtractHttpResponse
]


@dataclass(frozen=True, repr=False)
class TavilyExtractConfig:
    api_key: SecretValue
    timeout_seconds: float = 15.0
    max_payload_bytes: int = 5_000_000
    endpoint: str = TAVILY_EXTRACT_URL

    def __init__(
        self,
        *,
        api_key: SecretValue | str,
        timeout_seconds: float = 15.0,
        max_payload_bytes: int = 5_000_000,
        endpoint: str = TAVILY_EXTRACT_URL,
    ) -> None:
        object.__setattr__(
            self,
            "api_key",
            api_key if isinstance(api_key, SecretValue) else SecretValue(api_key),
        )
        object.__setattr__(self, "timeout_seconds", timeout_seconds)
        object.__setattr__(self, "max_payload_bytes", max_payload_bytes)
        object.__setattr__(self, "endpoint", endpoint)
        if endpoint != TAVILY_EXTRACT_URL:
            raise ValueError("Tavily Extract must use the pinned official HTTPS endpoint")
        if timeout_seconds <= 0 or max_payload_bytes <= 0:
            raise ValueError("Tavily Extract network limits must be positive")


@dataclass(frozen=True)
class ExtractedArticle:
    url: str
    content: str


@dataclass(frozen=True)
class TavilyExtractResult:
    articles: tuple[ExtractedArticle, ...]
    failed_urls: tuple[str, ...]
    usage: ProviderUsage
    request_id: str | None = None


class TavilyExtractProvider:
    """Extract at most five URLs per application batch using Basic mode."""

    def __init__(
        self,
        config: TavilyExtractConfig,
        *,
        transport: ExtractTransport | None = None,
    ) -> None:
        self._config = config
        self._transport = transport or _post_json

    def extract(self, urls: tuple[str, ...], *, query: str | None = None) -> TavilyExtractResult:
        unique_urls = tuple(dict.fromkeys(urls))
        if not 1 <= len(unique_urls) <= 5 or any(not _is_https_url(url) for url in unique_urls):
            raise ValueError("Tavily Extract batches require one to five unique HTTPS URLs")
        payload: dict[str, object] = {
            "urls": list(unique_urls),
            "extract_depth": "basic",
            "format": "text",
            "include_usage": True,
        }
        if query and query.strip():
            payload["query"] = query.strip()[:500]
            payload["chunks_per_source"] = 3
        response = self._transport(
            self._config.endpoint,
            {
                "Accept": "application/json",
                "Authorization": f"Bearer {self._config.api_key.reveal()}",
                "Content-Type": "application/json",
                "User-Agent": "TradingIG-market-intelligence/0.1",
            },
            json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            self._config.timeout_seconds,
            self._config.max_payload_bytes,
        )
        return self._parse_response(response, requested_urls=unique_urls)

    def _parse_response(
        self,
        response: TavilyExtractHttpResponse,
        *,
        requested_urls: tuple[str, ...],
    ) -> TavilyExtractResult:
        if response.final_url != self._config.endpoint:
            raise TavilyExtractError("Tavily Extract response redirected")
        if response.content_type.partition(";")[0].strip().lower() != "application/json":
            raise TavilyExtractError("Tavily Extract response is not JSON")
        if not response.body or len(response.body) > self._config.max_payload_bytes:
            raise TavilyExtractError("Tavily Extract response violates payload limits")
        try:
            payload = json.loads(response.body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TavilyExtractError("Tavily Extract response is invalid JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise TavilyExtractError("Tavily Extract response has no results")
        requested = set(requested_urls)
        articles: list[ExtractedArticle] = []
        for item in payload["results"]:
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            content = item.get("raw_content", item.get("content"))
            if not isinstance(url, str) or url not in requested or not isinstance(content, str):
                continue
            normalized = " ".join(content.split())[:12_000]
            if normalized:
                articles.append(ExtractedArticle(url=url, content=normalized))
        failed: list[str] = []
        raw_failed = payload.get("failed_results", [])
        if isinstance(raw_failed, list):
            for item in raw_failed:
                url = item.get("url") if isinstance(item, dict) else None
                if isinstance(url, str) and url in requested and url not in failed:
                    failed.append(url)
        returned = {article.url for article in articles}
        failed.extend(url for url in requested_urls if url not in returned and url not in failed)
        usage_document = payload.get("usage")
        credits = (
            usage_document.get("credits")
            if isinstance(usage_document, dict)
            else None
        )
        if not isinstance(credits, int) or credits < 0:
            credits = math.ceil(len(articles) / 5)
        request_id = payload.get("request_id")
        return TavilyExtractResult(
            articles=tuple(articles),
            failed_urls=tuple(failed),
            usage=ProviderUsage(credits=credits),
            request_id=(
                request_id.strip()
                if isinstance(request_id, str) and request_id.strip()
                else None
            ),
        )


def _is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme.lower() == "https" and bool(parsed.hostname)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        return None


def _post_json(
    url: str,
    headers: Mapping[str, str],
    body: bytes,
    timeout: float,
    max_bytes: int,
) -> TavilyExtractHttpResponse:
    request = Request(url, data=body, headers=dict(headers), method="POST")
    opener = build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:  # noqa: S310 - pinned HTTPS
            payload = response.read(max_bytes + 1)
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
    except HTTPError as exc:
        reason = "TAVILY_QUOTA_EXHAUSTED" if exc.code == 429 else "TAVILY_EXTRACT_HTTP_ERROR"
        raise TavilyExtractError("Tavily Extract HTTP request failed", reason_code=reason) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise TavilyExtractError(
            "Tavily Extract request failed", reason_code="TAVILY_EXTRACT_NETWORK_ERROR"
        ) from exc
    if len(payload) > max_bytes:
        raise TavilyExtractError("Tavily Extract response exceeds payload limit")
    return TavilyExtractHttpResponse(payload, final_url, content_type)
