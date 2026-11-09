from datetime import UTC, datetime, timedelta

import pytest

from trading_ig_assistant.adapters.official_rss_news import (
    ECB_PRESS_RSS_URL,
    FED_MONETARY_RSS_URL,
    FetchedDocument,
    OfficialRssError,
    OfficialRssNewsProvider,
    RssFeedConfig,
    ecb_press_news_provider,
    federal_reserve_monetary_news_provider,
)
from trading_ig_assistant.domain.context_sources import (
    ContextCategory,
    ContextImportance,
    ProviderCollectionStatus,
    SourceUsageRights,
)
from trading_ig_assistant.services.news_collection_service import collect_news

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


def _rss(*items: str) -> bytes:
    joined = "".join(items)
    return f'<?xml version="1.0"?><rss version="2.0"><channel>{joined}</channel></rss>'.encode()


def _item(
    *,
    title: str = "Official monetary policy release",
    link: str = "https://official.example/releases/1",
    guid: str = "official-release-1",
    published: str = "Wed, 04 Nov 2026 10:00:00 GMT",
) -> str:
    return (
        f"<item><title>{title}</title><link>{link}</link><guid>{guid}</guid>"
        f"<pubDate>{published}</pubDate></item>"
    )


def _provider(body: bytes, *, final_url: str = "https://official.example/feed.xml"):
    def fetcher(url: str, timeout: float, max_bytes: int, user_agent: str) -> FetchedDocument:
        assert url == "https://official.example/feed.xml"
        assert timeout == 5.0
        assert max_bytes == 1_000_000
        assert user_agent.startswith("TradingIG-context/")
        return FetchedDocument(
            body=body, final_url=final_url, content_type="text/xml; charset=utf-8"
        )

    return OfficialRssNewsProvider(
        RssFeedConfig(
            provider_id="official-test-rss",
            feed_url="https://official.example/feed.xml",
            source_name="Official Test Source",
            category=ContextCategory.CENTRAL_BANK,
            allowed_hosts=("official.example",),
        ),
        fetcher=fetcher,
    )


def test_official_rss_normalizes_metadata_without_inventing_importance() -> None:
    provider = _provider(_rss(_item()))

    items = provider.fetch_news(as_of_utc=NOW)

    assert len(items) == 1
    item = items[0]
    assert item.headline == "Official monetary policy release"
    assert item.published_at_utc == datetime(2026, 11, 4, 10, 0, tzinfo=UTC)
    assert item.observed_at_utc == NOW
    assert item.category is ContextCategory.CENTRAL_BANK
    assert item.importance is ContextImportance.UNKNOWN
    assert item.summary is None
    assert item.usage_rights is SourceUsageRights.METADATA_ONLY
    assert item.tags == ("official-test-rss", "rss", "central_bank")


def test_rss_order_and_ids_are_deterministic() -> None:
    earlier = _item(guid="early", published="Wed, 04 Nov 2026 09:00:00 GMT")
    later = _item(guid="late", published="Wed, 04 Nov 2026 11:00:00 GMT")
    provider = _provider(_rss(earlier, later))

    first = provider.fetch_news(as_of_utc=NOW)
    second = provider.fetch_news(as_of_utc=NOW)

    assert first[0].published_at_utc > first[1].published_at_utc
    assert tuple(item.item_id for item in first) == tuple(item.item_id for item in second)


@pytest.mark.parametrize(
    ("body", "match"),
    (
        (b"not xml", "invalid XML"),
        (_rss(_item(published="not-a-date")), "invalid publication"),
        (
            _rss(_item(published="Wed, 04 Nov 2026 13:00:00 GMT")),
            "future-dated",
        ),
        (_rss(_item(link="https://untrusted.example/release")), "allowed host"),
        (b'<!DOCTYPE rss [<!ENTITY x "x">]><rss><channel/></rss>', "document type"),
    ),
)
def test_invalid_or_untrusted_rss_is_rejected(body: bytes, match: str) -> None:
    provider = _provider(body)

    with pytest.raises((OfficialRssError, ValueError), match=match):
        provider.fetch_news(as_of_utc=NOW)


def test_response_redirect_and_content_type_are_constrained() -> None:
    redirected = _provider(_rss(), final_url="https://untrusted.example/feed.xml")
    with pytest.raises(OfficialRssError):
        redirected.fetch_news(as_of_utc=NOW)

    def fetcher(*_args) -> FetchedDocument:
        return FetchedDocument(
            body=_rss(),
            final_url="https://official.example/feed.xml",
            content_type="text/html",
        )

    provider = OfficialRssNewsProvider(
        RssFeedConfig(
            provider_id="official-test-rss",
            feed_url="https://official.example/feed.xml",
            source_name="Official Test Source",
            category=ContextCategory.CENTRAL_BANK,
            allowed_hosts=("official.example",),
        ),
        fetcher=fetcher,
    )
    with pytest.raises(OfficialRssError, match="content type"):
        provider.fetch_news(as_of_utc=NOW)


def test_provider_failure_degrades_to_explicit_unavailable_snapshot() -> None:
    provider = _provider(b"invalid")

    snapshot = collect_news(provider, as_of_utc=NOW)

    assert snapshot.status is ProviderCollectionStatus.UNAVAILABLE
    assert snapshot.items == ()
    assert snapshot.reason_codes == ("NEWS_PROVIDER_ERROR",)


def test_successful_collection_preserves_provider_and_items() -> None:
    provider = _provider(_rss(_item()))

    snapshot = collect_news(provider, as_of_utc=NOW)

    assert snapshot.status is ProviderCollectionStatus.AVAILABLE
    assert snapshot.provider_id == "official-test-rss"
    assert len(snapshot.items) == 1
    assert snapshot.reason_codes == ()


def test_broken_provider_identity_and_non_utc_collection_are_rejected_safely() -> None:
    class BrokenProvider:
        @property
        def provider_id(self):
            raise RuntimeError("synthetic identity failure")

    snapshot = collect_news(BrokenProvider(), as_of_utc=NOW)
    assert snapshot.status is ProviderCollectionStatus.UNAVAILABLE
    assert snapshot.provider_id == "invalid-news-provider"

    with pytest.raises(ValueError, match="UTC"):
        collect_news(BrokenProvider(), as_of_utc=NOW.replace(tzinfo=None))


def test_official_factories_pin_expected_https_sources() -> None:
    captured: list[str] = []

    def fetcher(url: str, *_args) -> FetchedDocument:
        captured.append(url)
        return FetchedDocument(body=_rss(), final_url=url, content_type="application/rss+xml")

    fed = federal_reserve_monetary_news_provider(fetcher=fetcher)
    ecb = ecb_press_news_provider(fetcher=fetcher)

    assert fed.fetch_news(as_of_utc=NOW) == ()
    assert ecb.fetch_news(as_of_utc=NOW) == ()
    assert captured == [FED_MONETARY_RSS_URL, ECB_PRESS_RSS_URL]


def test_payload_size_and_duplicate_items_are_rejected() -> None:
    provider = _provider(b"x" * 1_000_001)
    with pytest.raises(OfficialRssError, match="payload size"):
        provider.fetch_news(as_of_utc=NOW)

    duplicate = _item()
    provider = _provider(_rss(duplicate, duplicate))
    with pytest.raises(OfficialRssError, match="duplicate"):
        provider.fetch_news(as_of_utc=NOW)


def test_publication_must_not_follow_observation() -> None:
    provider = _provider(_rss(_item(published="Wed, 04 Nov 2026 12:00:01 GMT")))
    with pytest.raises(OfficialRssError, match="future-dated"):
        provider.fetch_news(as_of_utc=NOW)

    snapshot = collect_news(provider, as_of_utc=NOW + timedelta(seconds=2))
    assert snapshot.status is ProviderCollectionStatus.AVAILABLE
