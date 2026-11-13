"""Read-only GDELT DOC 2.0 adapter for unconfirmed event discovery."""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from hashlib import sha256
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

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
    PublicationTimeStatus,
    VerificationStatus,
)

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


class GdeltNewsError(RuntimeError):
    """Raised when GDELT cannot satisfy the normalized metadata contract."""

    def __init__(
        self,
        message: str,
        *,
        reason_code: str = "GDELT_PROVIDER_ERROR",
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class GdeltHttpResponse:
    body: bytes
    final_url: str
    content_type: str


GdeltTransport = Callable[[str, Mapping[str, str], float, int], GdeltHttpResponse]


@dataclass(frozen=True)
class GdeltNewsConfig:
    timeout_seconds: float = 8.0
    max_payload_bytes: int = 2_000_000
    endpoint: str = GDELT_DOC_URL

    def __post_init__(self) -> None:
        if self.endpoint != GDELT_DOC_URL:
            raise ValueError("GDELT DOC must use the pinned official HTTPS endpoint")
        if self.timeout_seconds <= 0 or self.max_payload_bytes <= 0:
            raise ValueError("GDELT network limits must be positive")


class GdeltNewsProvider:
    """Discover geopolitical coverage without inferring confirmation or direction."""

    provider_id = "gdelt-doc"

    def __init__(
        self,
        config: GdeltNewsConfig | None = None,
        *,
        transport: GdeltTransport | None = None,
    ) -> None:
        self._config = config or GdeltNewsConfig()
        self._transport = transport or _get_json

    def search_news(
        self,
        request: NewsSearchRequest,
        *,
        as_of_utc: datetime,
    ) -> IntelligenceProviderResult:
        _require_utc(as_of_utc)
        url = _request_url(self._config.endpoint, request)
        headers = {
            "Accept": "application/json",
            "User-Agent": "TradingIG-market-intelligence/0.1",
        }
        try:
            response = self._transport(
                url,
                headers,
                self._config.timeout_seconds,
                self._config.max_payload_bytes,
            )
            return self._parse_response(
                response,
                expected_url=url,
                request=request,
                as_of_utc=as_of_utc,
            )
        except GdeltNewsError:
            raise
        except Exception as exc:
            raise GdeltNewsError("GDELT news retrieval failed") from exc

    def _parse_response(
        self,
        response: GdeltHttpResponse,
        *,
        expected_url: str,
        request: NewsSearchRequest,
        as_of_utc: datetime,
    ) -> IntelligenceProviderResult:
        if response.final_url != expected_url:
            raise GdeltNewsError("GDELT response redirected")
        content_type = response.content_type.partition(";")[0].strip().lower()
        if content_type not in {"application/json", "text/json"}:
            raise GdeltNewsError("GDELT response has an unsupported content type")
        if not response.body or len(response.body) > self._config.max_payload_bytes:
            raise GdeltNewsError("GDELT response violates the payload size limit")
        try:
            payload = json.loads(response.body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GdeltNewsError("GDELT response is invalid JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("articles"), list):
            raise GdeltNewsError("GDELT response has no article list")
        articles = payload["articles"]
        if len(articles) > request.max_results:
            raise GdeltNewsError("GDELT response exceeds the requested result limit")
        records: list[IntelligenceNewsRecord] = []
        seen_ids: set[str] = set()
        for raw in articles:
            record = _parse_record(raw, request=request, as_of_utc=as_of_utc)
            if record is None or record.news.item_id in seen_ids:
                continue
            seen_ids.add(record.news.item_id)
            records.append(record)
        records.sort(
            key=lambda item: (item.news.published_at_utc, item.news.item_id),
            reverse=True,
        )
        return IntelligenceProviderResult(
            provider_id=self.provider_id,
            provider_kind=IntelligenceProviderKind.GDELT,
            query=request.query,
            records=tuple(records),
            observed_at_utc=as_of_utc,
        )


def _request_url(endpoint: str, request: NewsSearchRequest) -> str:
    params: dict[str, str] = {
        "query": request.query.strip(),
        "mode": "ArtList",
        "format": "json",
        "maxrecords": str(request.max_results),
        "sort": "HybridRel",
    }
    if request.start_at_utc is not None:
        params["startdatetime"] = request.start_at_utc.strftime("%Y%m%d%H%M%S")
    if request.end_at_utc is not None:
        params["enddatetime"] = request.end_at_utc.strftime("%Y%m%d%H%M%S")
    if request.recent_window is not None:
        minutes = max(15, math.ceil(request.recent_window.total_seconds() / 60))
        params["timespan"] = f"{minutes}min"
    return f"{endpoint}?{urlencode(params)}"


def _parse_record(
    value: object,
    *,
    request: NewsSearchRequest,
    as_of_utc: datetime,
) -> IntelligenceNewsRecord | None:
    if not isinstance(value, dict):
        raise GdeltNewsError("GDELT article must be an object")
    raw_title = value.get("title")
    url = value.get("url")
    if not isinstance(raw_title, str) or not raw_title.strip():
        return None
    if not isinstance(url, str) or not _is_https_url(url):
        return None
    title = " ".join(raw_title.split())[:300]
    raw_seen = value.get("seendate")
    if isinstance(raw_seen, str) and raw_seen.strip():
        published = _parse_seen_date(raw_seen)
        publication_status = PublicationTimeStatus.PROVIDER_ESTIMATE
        if published > as_of_utc:
            return None
    else:
        published = as_of_utc
        publication_status = PublicationTimeStatus.UNKNOWN
    identity = f"{url}\0{title}\0{published.isoformat()}"
    item_id = sha256(f"gdelt-doc\0{identity}".encode()).hexdigest()
    domain = value.get("domain")
    source = (
        domain.strip().lower()
        if isinstance(domain, str) and domain.strip()
        else (urlparse(url).hostname or "GDELT result").lower()
    )
    tags = (
        "gdelt-doc",
        "event_discovery",
        request.category.value,
        f"publication_time:{publication_status.value}",
        "verification:unconfirmed",
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
        source=source,
        source_url=url,
        usage_rights=SourceUsageRights.METADATA_ONLY,
        tags=tags,
    )
    return IntelligenceNewsRecord(
        news=news,
        provider_id="gdelt-doc",
        provider_kind=IntelligenceProviderKind.GDELT,
        publication_time_status=publication_status,
        verification_status=VerificationStatus.UNCONFIRMED,
    )


def _parse_seen_date(value: str) -> datetime:
    compact = value.strip().upper()
    formats = ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S")
    for pattern in formats:
        try:
            return datetime.strptime(compact, pattern).replace(tzinfo=UTC)
        except ValueError:
            continue
    raise GdeltNewsError("GDELT article has an invalid seen date")


def _is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme.lower() == "https" and bool(parsed.hostname)


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("GDELT observation timestamp must use UTC")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        return None


def _get_json(
    url: str,
    headers: Mapping[str, str],
    timeout: float,
    max_bytes: int,
) -> GdeltHttpResponse:
    request = Request(url, headers=dict(headers), method="GET")
    opener = build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:  # noqa: S310 - pinned HTTPS
            payload = response.read(max_bytes + 1)
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
    except HTTPError as exc:
        reason_code = "GDELT_RATE_LIMITED" if exc.code == 429 else "GDELT_HTTP_ERROR"
        raise GdeltNewsError(
            "GDELT HTTP request failed",
            reason_code=reason_code,
            retry_after_seconds=_retry_after_seconds(
                exc.headers.get("Retry-After") if exc.headers is not None else None
            ),
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise GdeltNewsError(
            "GDELT HTTP request failed",
            reason_code="GDELT_NETWORK_ERROR",
        ) from exc
    if len(payload) > max_bytes:
        raise GdeltNewsError("GDELT response exceeds the payload size limit")
    return GdeltHttpResponse(payload, final_url, content_type)


def _retry_after_seconds(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    text = value.strip()
    try:
        return max(1, int(text))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        return max(1, math.ceil((retry_at.astimezone(UTC) - datetime.now(UTC)).total_seconds()))
