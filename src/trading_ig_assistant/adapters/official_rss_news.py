"""Strict read-only adapters for configured official RSS news feeds."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from hashlib import sha256
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from trading_ig_assistant.domain.context_sources import (
    ContextCategory,
    ContextImportance,
    NewsItem,
    SourceUsageRights,
)

FED_MONETARY_RSS_URL = "https://www.federalreserve.gov/feeds/press_monetary.xml"
ECB_PRESS_RSS_URL = "https://www.ecb.europa.eu/rss/press.html"


class OfficialRssError(RuntimeError):
    """Raised when an official feed cannot satisfy the normalized contract."""


@dataclass(frozen=True)
class FetchedDocument:
    body: bytes
    final_url: str
    content_type: str


RssFetcher = Callable[[str, float, int, str], FetchedDocument]


@dataclass(frozen=True)
class RssFeedConfig:
    provider_id: str
    feed_url: str
    source_name: str
    category: ContextCategory
    allowed_hosts: tuple[str, ...]
    timeout_seconds: float = 5.0
    max_payload_bytes: int = 1_000_000
    max_items: int = 50

    def __post_init__(self) -> None:
        if not self.provider_id.strip() or not self.source_name.strip():
            raise ValueError("RSS provider identity and source name are required")
        if self.timeout_seconds <= 0 or self.max_payload_bytes <= 0 or self.max_items <= 0:
            raise ValueError("RSS network and item limits must be positive")
        if any(not host.strip() for host in self.allowed_hosts) or not self.allowed_hosts:
            raise ValueError("RSS provider requires explicit allowed hosts")
        _require_allowed_https_url(self.feed_url, self.allowed_hosts, "RSS feed")


class OfficialRssNewsProvider:
    """Fetch and normalize metadata from one allowlisted official RSS 2.0 feed."""

    def __init__(self, config: RssFeedConfig, *, fetcher: RssFetcher | None = None) -> None:
        self._config = config
        self._fetcher = fetcher or _fetch_document

    @property
    def provider_id(self) -> str:
        return self._config.provider_id

    def fetch_news(self, *, as_of_utc: datetime) -> tuple[NewsItem, ...]:
        _require_utc(as_of_utc)
        try:
            document = self._fetcher(
                self._config.feed_url,
                self._config.timeout_seconds,
                self._config.max_payload_bytes,
                "TradingIG-context/0.1",
            )
            return self._parse_document(document, as_of_utc)
        except OfficialRssError:
            raise
        except Exception as exc:
            raise OfficialRssError("official RSS retrieval failed") from exc

    def _parse_document(
        self,
        document: FetchedDocument,
        as_of_utc: datetime,
    ) -> tuple[NewsItem, ...]:
        _require_allowed_https_url(
            document.final_url,
            self._config.allowed_hosts,
            "RSS response",
            runtime=True,
        )
        content_type = document.content_type.partition(";")[0].strip().lower()
        if content_type not in {"application/rss+xml", "application/xml", "text/xml"}:
            raise OfficialRssError("official RSS response has an unsupported content type")
        if not document.body or len(document.body) > self._config.max_payload_bytes:
            raise OfficialRssError("official RSS response violates the payload size limit")
        if b"<!DOCTYPE" in document.body.upper():
            raise OfficialRssError("official RSS response contains a forbidden document type")
        try:
            root = ElementTree.fromstring(document.body)
        except ElementTree.ParseError as exc:
            raise OfficialRssError("official RSS response is invalid XML") from exc
        if _local_name(root.tag) != "rss":
            raise OfficialRssError("official RSS response is not an RSS document")
        channel = next((child for child in root if _local_name(child.tag) == "channel"), None)
        if channel is None:
            raise OfficialRssError("official RSS response has no channel")

        items: list[NewsItem] = []
        seen_ids: set[str] = set()
        for node in (child for child in channel if _local_name(child.tag) == "item"):
            title = _required_child_text(node, "title")
            link = _required_child_text(node, "link")
            guid = _child_text(node, "guid") or link
            published = _parse_rfc2822(_required_child_text(node, "pubDate"))
            if published > as_of_utc:
                raise OfficialRssError("official RSS item is future-dated")
            _require_allowed_https_url(
                link,
                self._config.allowed_hosts,
                "RSS item",
                runtime=True,
            )
            item_id = sha256(
                f"{self.provider_id}\0{guid}\0{published.isoformat()}".encode()
            ).hexdigest()
            if item_id in seen_ids:
                raise OfficialRssError("official RSS response contains duplicate items")
            seen_ids.add(item_id)
            items.append(
                NewsItem(
                    schema_version=1,
                    item_id=item_id,
                    headline=title,
                    summary=None,
                    category=self._config.category,
                    importance=ContextImportance.UNKNOWN,
                    published_at_utc=published,
                    observed_at_utc=as_of_utc,
                    source=self._config.source_name,
                    source_url=link,
                    usage_rights=SourceUsageRights.METADATA_ONLY,
                    tags=(self.provider_id, "rss", self._config.category.value),
                )
            )
        items.sort(key=lambda item: (item.published_at_utc, item.item_id), reverse=True)
        return tuple(items[: self._config.max_items])


def federal_reserve_monetary_news_provider(
    *, fetcher: RssFetcher | None = None
) -> OfficialRssNewsProvider:
    return OfficialRssNewsProvider(
        RssFeedConfig(
            provider_id="federal-reserve-monetary-rss",
            feed_url=FED_MONETARY_RSS_URL,
            source_name="Federal Reserve Board",
            category=ContextCategory.CENTRAL_BANK,
            allowed_hosts=("www.federalreserve.gov",),
        ),
        fetcher=fetcher,
    )


def ecb_press_news_provider(*, fetcher: RssFetcher | None = None) -> OfficialRssNewsProvider:
    return OfficialRssNewsProvider(
        RssFeedConfig(
            provider_id="ecb-press-rss",
            feed_url=ECB_PRESS_RSS_URL,
            source_name="European Central Bank",
            category=ContextCategory.CENTRAL_BANK,
            allowed_hosts=("www.ecb.europa.eu",),
        ),
        fetcher=fetcher,
    )


def _fetch_document(url: str, timeout: float, max_bytes: int, user_agent: str) -> FetchedDocument:
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - HTTPS is allowlisted
        body = response.read(max_bytes + 1)
        final_url = response.geturl()
        content_type = response.headers.get("Content-Type", "")
    if len(body) > max_bytes:
        raise OfficialRssError("official RSS response exceeds the payload size limit")
    return FetchedDocument(body=body, final_url=final_url, content_type=content_type)


def _child_text(node: ElementTree.Element, name: str) -> str | None:
    child = next((item for item in node if _local_name(item.tag) == name), None)
    if child is None or child.text is None or not child.text.strip():
        return None
    return child.text.strip()


def _required_child_text(node: ElementTree.Element, name: str) -> str:
    value = _child_text(node, name)
    if value is None:
        raise OfficialRssError(f"official RSS item has no {name}")
    return value


def _parse_rfc2822(value: str) -> datetime:
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError) as exc:
        raise OfficialRssError("official RSS item has an invalid publication timestamp") from exc
    if parsed.tzinfo is None:
        raise OfficialRssError("official RSS publication timestamp has no timezone")
    return parsed.astimezone(UTC)


def _require_allowed_https_url(
    url: str,
    allowed_hosts: tuple[str, ...],
    label: str,
    *,
    runtime: bool = False,
) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https" or host not in {item.lower() for item in allowed_hosts}:
        message = f"{label} URL must use HTTPS on an allowed host"
        if runtime:
            raise OfficialRssError(message)
        raise ValueError(message)


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("news collection timestamp must use UTC")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
