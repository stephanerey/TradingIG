"""Bounded Tavily Basic Search adapter with transient short content."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from hashlib import sha256
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.domain.context_sources import (
    ContextImportance,
    NewsItem,
    SourceUsageRights,
)
from trading_ig_assistant.domain.market_intelligence import (
    IntelligenceNewsRecord,
    IntelligenceProviderKind,
    IntelligenceProviderResult,
    NewsSearchRequest,
    ProviderUsage,
    PublicationTimeStatus,
    VerificationStatus,
)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"
_LOGGER = logging.getLogger(__name__)


class TavilyNewsError(RuntimeError):
    """Raised when Tavily cannot satisfy the normalized metadata contract."""

    def __init__(self, message: str, *, reason_code: str = "TAVILY_PROVIDER_ERROR") -> None:
        super().__init__(message)
        self.reason_code = reason_code


@dataclass(frozen=True)
class TavilyHttpResponse:
    body: bytes
    final_url: str
    content_type: str


TavilyTransport = Callable[
    [str, Mapping[str, str], bytes, float, int],
    TavilyHttpResponse,
]


@dataclass(frozen=True, repr=False)
class TavilyNewsConfig:
    api_key: SecretValue
    timeout_seconds: float = 8.0
    max_payload_bytes: int = 1_000_000
    endpoint: str = TAVILY_SEARCH_URL

    def __init__(
        self,
        *,
        api_key: SecretValue | str,
        timeout_seconds: float = 8.0,
        max_payload_bytes: int = 1_000_000,
        endpoint: str = TAVILY_SEARCH_URL,
    ) -> None:
        object.__setattr__(
            self,
            "api_key",
            api_key if isinstance(api_key, SecretValue) else SecretValue(api_key),
        )
        object.__setattr__(self, "timeout_seconds", timeout_seconds)
        object.__setattr__(self, "max_payload_bytes", max_payload_bytes)
        object.__setattr__(self, "endpoint", endpoint)
        if endpoint != TAVILY_SEARCH_URL:
            raise ValueError("Tavily Search must use the pinned official HTTPS endpoint")
        if timeout_seconds <= 0 or max_payload_bytes <= 0:
            raise ValueError("Tavily network limits must be positive")


class TavilyNewsProvider:
    """Search Tavily in Basic news mode and retain snippets in memory only."""

    provider_id = "tavily-news"

    def __init__(
        self,
        config: TavilyNewsConfig,
        *,
        transport: TavilyTransport | None = None,
    ) -> None:
        self._config = config
        self._transport = transport or _post_json

    def search_news(
        self,
        request: NewsSearchRequest,
        *,
        as_of_utc: datetime,
    ) -> IntelligenceProviderResult:
        _require_utc(as_of_utc)
        payload = _request_payload(request, as_of_utc=as_of_utc)
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._config.api_key.reveal()}",
            "Content-Type": "application/json",
            "User-Agent": "TradingIG-market-intelligence/0.1",
        }
        try:
            response = self._transport(
                self._config.endpoint,
                headers,
                json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                self._config.timeout_seconds,
                self._config.max_payload_bytes,
            )
            result = self._parse_response(
                response,
                request=request,
                as_of_utc=as_of_utc,
            )
        except TavilyNewsError:
            raise
        except Exception as exc:
            raise TavilyNewsError("Tavily news retrieval failed") from exc
        _LOGGER.info(
            "Tavily news search completed query_hash=%s credits=%d results=%d",
            sha256(request.query.encode("utf-8")).hexdigest()[:12],
            result.usage.credits if result.usage else 0,
            len(result.records),
        )
        return result

    def _parse_response(
        self,
        response: TavilyHttpResponse,
        *,
        request: NewsSearchRequest,
        as_of_utc: datetime,
    ) -> IntelligenceProviderResult:
        if response.final_url != self._config.endpoint:
            raise TavilyNewsError("Tavily response redirected")
        content_type = response.content_type.partition(";")[0].strip().lower()
        if content_type != "application/json":
            raise TavilyNewsError("Tavily response has an unsupported content type")
        if not response.body or len(response.body) > self._config.max_payload_bytes:
            raise TavilyNewsError("Tavily response violates the payload size limit")
        try:
            payload = json.loads(response.body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TavilyNewsError("Tavily response is invalid JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise TavilyNewsError("Tavily response has no result list")
        raw_results = payload["results"]
        if len(raw_results) > request.max_results:
            raise TavilyNewsError("Tavily response exceeds the requested result limit")
        usage = payload.get("usage")
        if not isinstance(usage, dict) or not isinstance(usage.get("credits"), int):
            raise TavilyNewsError("Tavily response has no exact credit usage")
        if usage["credits"] < 0:
            raise TavilyNewsError("Tavily credit usage is invalid")

        records: list[IntelligenceNewsRecord] = []
        seen_ids: set[str] = set()
        for raw in raw_results:
            record = _parse_record(
                raw,
                request=request,
                as_of_utc=as_of_utc,
            )
            if record is None:
                continue
            if record.news.item_id in seen_ids:
                continue
            seen_ids.add(record.news.item_id)
            records.append(record)
        records.sort(
            key=lambda item: (item.news.published_at_utc, item.news.item_id),
            reverse=True,
        )
        _LOGGER.info(
            "Tavily response normalized raw_results=%d accepted_results=%d "
            "discarded_results=%d",
            len(raw_results),
            len(records),
            len(raw_results) - len(records),
        )
        request_id = payload.get("request_id")
        return IntelligenceProviderResult(
            provider_id=self.provider_id,
            provider_kind=IntelligenceProviderKind.TAVILY,
            query=request.query,
            records=tuple(records),
            observed_at_utc=as_of_utc,
            usage=ProviderUsage(credits=usage["credits"]),
            request_id=(
                request_id.strip()
                if isinstance(request_id, str) and request_id.strip()
                else None
            ),
        )


def _request_payload(
    request: NewsSearchRequest,
    *,
    as_of_utc: datetime,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "query": request.query.strip(),
        "topic": "news",
        "search_depth": "basic",
        "max_results": request.max_results,
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
        "include_published_date": True,
        "include_usage": True,
        "auto_parameters": False,
    }
    if request.start_at_utc is not None:
        payload["start_date"] = request.start_at_utc.date().isoformat()
    if request.end_at_utc is not None:
        payload["end_date"] = request.end_at_utc.date().isoformat()
    if request.start_at_utc is not None or request.end_at_utc is not None:
        # Keep undated results. The adapter marks their date as unknown and the
        # bounded local policy decides whether they can be used by the AI.
        payload["filter_by_published_date"] = False
    elif request.recent_window is not None:
        # Tavily's max_age_hours controls cache freshness, not publication age.
        # Use a publication-date range for discovery and enforce the exact
        # hour-level boundary again in _parse_record.
        payload["start_date"] = (as_of_utc - request.recent_window).date().isoformat()
        payload["end_date"] = (as_of_utc.date() + timedelta(days=1)).isoformat()
        payload["filter_by_published_date"] = False
    return payload


def _parse_record(
    value: object,
    *,
    request: NewsSearchRequest,
    as_of_utc: datetime,
) -> IntelligenceNewsRecord | None:
    if not isinstance(value, dict):
        raise TavilyNewsError("Tavily result must be an object")
    title = _bounded_title(value.get("title"))
    url = value.get("url")
    if not title or not isinstance(url, str) or not _is_https_url(url):
        return None
    published_raw = value.get("published_date")
    if published_raw is None or not str(published_raw).strip():
        published = as_of_utc
        publication_status = PublicationTimeStatus.UNKNOWN
    else:
        published = _parse_datetime(str(published_raw))
        publication_status = PublicationTimeStatus.PROVIDER_ESTIMATE
        if published > as_of_utc:
            return None
        if request.recent_window is not None:
            oldest_allowed = as_of_utc - request.recent_window
            if published < oldest_allowed:
                return None
        if request.start_at_utc is not None and published < request.start_at_utc:
            return None
        if request.end_at_utc is not None and published >= request.end_at_utc:
            return None
    score = value.get("score")
    relevance = float(score) if isinstance(score, (int, float)) and 0 <= score <= 1 else None
    search_excerpt = _bounded_excerpt(value.get("content"))
    provider_record_id = value.get("id")
    identity = (
        provider_record_id.strip()
        if isinstance(provider_record_id, str) and provider_record_id.strip()
        else f"{url}\0{title}\0{published.isoformat()}"
    )
    item_id = sha256(f"tavily-news\0{identity}".encode()).hexdigest()
    host = (urlparse(url).hostname or "Tavily result").lower()
    tags = (
        "tavily-news",
        "news_search",
        request.category.value,
        f"publication_time:{publication_status.value}",
        "verification:single_source",
    )
    news = NewsItem(
        schema_version=1,
        item_id=item_id,
        headline=title,
        summary=None,
        category=request.category,
        importance=ContextImportance.UNKNOWN,
        published_at_utc=published,
        observed_at_utc=as_of_utc,
        source=host,
        source_url=url,
        usage_rights=SourceUsageRights.METADATA_ONLY,
        tags=tags,
    )
    return IntelligenceNewsRecord(
        news=news,
        provider_id="tavily-news",
        provider_kind=IntelligenceProviderKind.TAVILY,
        publication_time_status=publication_status,
        verification_status=VerificationStatus.SINGLE_SOURCE,
        relevance_score=relevance,
        search_excerpt=search_excerpt,
    )


def _bounded_title(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return " ".join(value.split())[:300]


def _bounded_excerpt(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    return normalized[:4_000] if normalized else None


def _parse_datetime(value: str) -> datetime:
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise TavilyNewsError("Tavily result has an invalid publication date") from exc
    if parsed.tzinfo is None:
        raise TavilyNewsError("Tavily publication date has no timezone")
    return parsed.astimezone(UTC)


def _is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme.lower() == "https" and bool(parsed.hostname)


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("Tavily observation timestamp must use UTC")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        return None


def _post_json(
    url: str,
    headers: Mapping[str, str],
    body: bytes,
    timeout: float,
    max_bytes: int,
) -> TavilyHttpResponse:
    request = Request(url, data=body, headers=dict(headers), method="POST")
    opener = build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:  # noqa: S310 - pinned HTTPS
            payload = response.read(max_bytes + 1)
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
    except HTTPError as exc:
        reason_code = "TAVILY_QUOTA_EXHAUSTED" if exc.code == 429 else "TAVILY_HTTP_ERROR"
        raise TavilyNewsError(
            "Tavily HTTP request failed",
            reason_code=reason_code,
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise TavilyNewsError(
            "Tavily HTTP request failed",
            reason_code="TAVILY_NETWORK_ERROR",
        ) from exc
    if len(payload) > max_bytes:
        raise TavilyNewsError("Tavily response exceeds the payload size limit")
    return TavilyHttpResponse(payload, final_url, content_type)
