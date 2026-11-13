"""Select and project bounded article evidence for advisory AI context."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from trading_ig_assistant.domain.ai_context import AI_EVIDENCE_TAG
from trading_ig_assistant.domain.context_sources import (
    NewsCollectionSnapshot,
    NewsItem,
    ProviderCollectionStatus,
    SourceUsageRights,
)
from trading_ig_assistant.domain.macro_context import ContextSeverity, ContextSignal
from trading_ig_assistant.domain.market_intelligence import (
    ArticleContentOrigin,
    ArticleEvidence,
    ArticleEvidenceBundle,
    IntelligenceNewsRecord,
    IntelligenceProviderKind,
)
from trading_ig_assistant.services.market_intelligence_scheduler import (
    IntelligenceFreshnessPolicy,
)

_SHORT_CONTENT_MINIMUM = 500


def select_ai_article_candidates(
    records: tuple[IntelligenceNewsRecord, ...],
    *,
    generated_at_utc: datetime,
    freshness_policy: IntelligenceFreshnessPolicy,
    max_items: int = 5,
) -> tuple[IntelligenceNewsRecord, ...]:
    """Rank quality, relevance and diversity; recency is only one component."""

    _require_utc(generated_at_utc)
    if not 1 <= max_items <= 5:
        raise ValueError("AI article selection is limited to five sources")
    deduplicated: dict[str, IntelligenceNewsRecord] = {}
    for record in records:
        age = generated_at_utc - record.news.published_at_utc
        if age < timedelta(0) or age > freshness_policy.for_category(record.news.category):
            continue
        key = _canonical_url(record.news.source_url) or record.news.headline.casefold()
        previous = deduplicated.get(key)
        if previous is None or _base_score(record, generated_at_utc) > _base_score(
            previous, generated_at_utc
        ):
            deduplicated[key] = record
    ranked = sorted(
        deduplicated.values(),
        key=lambda record: (
            _base_score(record, generated_at_utc),
            record.news.published_at_utc,
            record.news.item_id,
        ),
        reverse=True,
    )
    selected: list[IntelligenceNewsRecord] = []
    seen_sources: set[str] = set()
    seen_categories: set[str] = set()
    while ranked and len(selected) < max_items:
        best_index = max(
            range(len(ranked)),
            key=lambda index: _diversified_score(
                ranked[index],
                generated_at_utc,
                seen_sources=seen_sources,
                seen_categories=seen_categories,
            ),
        )
        record = ranked.pop(best_index)
        selected.append(record)
        seen_sources.add(record.news.source.casefold())
        seen_categories.add(record.news.category.value)
    return tuple(selected)


def build_article_evidence_bundle(
    records: tuple[IntelligenceNewsRecord, ...],
    *,
    generated_at_utc: datetime,
    freshness_policy: IntelligenceFreshnessPolicy,
    extracted_content: dict[str, str] | None = None,
    max_output_tokens: int = 600,
    model: str = "gpt-6-luna",
    tavily_extract_credits: int = 0,
    reason_codes: tuple[str, ...] = (),
) -> ArticleEvidenceBundle:
    selected = select_ai_article_candidates(
        records,
        generated_at_utc=generated_at_utc,
        freshness_policy=freshness_policy,
    )
    extracted = extracted_content or {}
    articles: list[ArticleEvidence] = []
    for record in selected:
        url = record.news.source_url
        if not url:
            continue
        excerpt = extracted.get(url)
        origin = ArticleContentOrigin.TAVILY_EXTRACT_BASIC
        if not excerpt:
            excerpt = record.search_excerpt
            origin = (
                ArticleContentOrigin.SEARCH_SNIPPET
                if excerpt
                else ArticleContentOrigin.METADATA_ONLY
            )
        articles.append(
            ArticleEvidence(
                signal_id=f"news:{record.news.item_id}",
                headline=record.news.headline,
                source=record.news.source,
                source_url=url,
                provider_id=record.provider_id,
                category=record.news.category,
                verification_status=record.verification_status,
                published_at_utc=record.news.published_at_utc,
                observed_at_utc=record.news.observed_at_utc,
                valid_until_utc=record.news.observed_at_utc
                + freshness_policy.for_category(record.news.category),
                excerpt=excerpt,
                content_origin=origin,
                relevance_score=record.relevance_score,
            )
        )
    if not articles:
        raise ValueError("no eligible article evidence is available")
    characters = sum(
        len(article.headline) + len(article.excerpt or "") + len(article.source_url)
        for article in articles
    )
    input_tokens = max(1, math.ceil(characters / 4))
    return ArticleEvidenceBundle(
        articles=tuple(articles),
        generated_at_utc=generated_at_utc,
        estimated_input_tokens=input_tokens,
        estimated_output_tokens=max_output_tokens,
        estimated_openai_cost_usd=_estimated_openai_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=max_output_tokens,
        ),
        tavily_extract_credits=tavily_extract_credits,
        reason_codes=reason_codes,
    )


def article_evidence_needing_extract(
    records: tuple[IntelligenceNewsRecord, ...],
) -> tuple[str, ...]:
    return tuple(
        record.news.source_url
        for record in records
        if record.news.source_url
        and len(record.search_excerpt or "") < _SHORT_CONTENT_MINIMUM
    )


def build_article_ai_evidence_signals(
    bundle: ArticleEvidenceBundle,
) -> tuple[ContextSignal, ...]:
    return tuple(
        ContextSignal(
            signal_id=article.signal_id,
            label=article.headline,
            severity=ContextSeverity.GRAY,
            score=None,
            summary=(
                article.excerpt
                or "Contenu indisponible ; titre et provenance uniquement."
            ),
            source=article.source,
            source_url=article.source_url,
            observed_at_utc=article.published_at_utc,
            valid_until_utc=article.valid_until_utc,
            confidence=None,
            tags=(
                AI_EVIDENCE_TAG,
                "article_excerpt" if article.excerpt else "article_metadata_only",
                article.category.value,
                f"provider:{article.provider_id}",
                f"content_origin:{article.content_origin.value}",
                f"verification:{article.verification_status.value}",
            ),
        )
        for article in bundle.articles
    )


def build_news_ai_evidence_signals(
    snapshots: tuple[NewsCollectionSnapshot, ...],
    *,
    generated_at_utc: datetime,
    valid_for: timedelta,
    max_items: int = 20,
) -> tuple[ContextSignal, ...]:
    """Return bounded headline metadata as gray evidence without deterministic score or bias."""

    _require_utc(generated_at_utc)
    if valid_for <= timedelta(0):
        raise ValueError("AI news-evidence validity must be positive")
    if max_items <= 0:
        raise ValueError("AI news-evidence item limit must be positive")

    items = [
        (item, snapshot.collected_at_utc + valid_for, snapshot.provider_id)
        for snapshot in snapshots
        if snapshot.status is ProviderCollectionStatus.AVAILABLE
        and snapshot.collected_at_utc <= generated_at_utc < snapshot.collected_at_utc + valid_for
        for item in snapshot.items
        if item.usage_rights is not SourceUsageRights.UNKNOWN
    ]
    selected = _select_provider_balanced(items, max_items=max_items)
    return tuple(
        ContextSignal(
            signal_id=f"news:{item.item_id}",
            label=item.headline,
            severity=ContextSeverity.GRAY,
            score=None,
            summary=(
                f"Metadata from {provider_id} published at "
                f"{item.published_at_utc.isoformat()}; "
                "no article body was collected."
            ),
            source=item.source,
            source_url=item.source_url,
            observed_at_utc=item.published_at_utc,
            valid_until_utc=valid_until_utc,
            confidence=None,
            tags=_evidence_tags(provider_id, item.category.value),
        )
        for item, valid_until_utc, provider_id in selected
    )


def _select_provider_balanced(
    items: list[tuple[NewsItem, datetime, str]],
    *,
    max_items: int,
) -> tuple[tuple[NewsItem, datetime, str], ...]:
    """Round-robin providers before sorting the bounded selection by recency."""

    by_provider: dict[str, list[tuple[NewsItem, datetime, str]]] = {}
    for entry in items:
        by_provider.setdefault(entry[2], []).append(entry)
    for entries in by_provider.values():
        entries.sort(
            key=lambda entry: (entry[0].published_at_utc, entry[0].item_id),
            reverse=True,
        )
    provider_order = sorted(
        by_provider,
        key=lambda provider_id: (
            by_provider[provider_id][0][0].published_at_utc,
            provider_id,
        ),
        reverse=True,
    )
    selected: list[tuple[NewsItem, datetime, str]] = []
    while provider_order and len(selected) < max_items:
        remaining: list[str] = []
        for provider_id in provider_order:
            entries = by_provider[provider_id]
            if entries and len(selected) < max_items:
                selected.append(entries.pop(0))
            if entries:
                remaining.append(provider_id)
        provider_order = remaining
    selected.sort(
        key=lambda entry: (entry[0].published_at_utc, entry[0].item_id),
        reverse=True,
    )
    return tuple(selected)


def _evidence_tags(provider_id: str, category: str) -> tuple[str, ...]:
    if provider_id in {"tavily-news", "gdelt-doc"}:
        return (
            AI_EVIDENCE_TAG,
            "discovery_news_metadata",
            category,
            f"provider:{provider_id}",
        )
    return (AI_EVIDENCE_TAG, "official_news_metadata", category)


def _base_score(record: IntelligenceNewsRecord, generated_at_utc: datetime) -> float:
    relevance = record.relevance_score if record.relevance_score is not None else 0.45
    verification = {
        IntelligenceProviderKind.OFFICIAL: 0.25,
        IntelligenceProviderKind.TAVILY: 0.15,
        IntelligenceProviderKind.GDELT: 0.0,
    }[record.provider_kind]
    content = min(0.15, len(record.search_excerpt or "") / 4_000 * 0.15)
    age_hours = max(
        0.0,
        (generated_at_utc - record.news.published_at_utc).total_seconds() / 3600,
    )
    recency = max(0.0, 0.15 - min(age_hours, 168) / 168 * 0.15)
    return relevance * 0.45 + verification + content + recency


def _diversified_score(
    record: IntelligenceNewsRecord,
    generated_at_utc: datetime,
    *,
    seen_sources: set[str],
    seen_categories: set[str],
) -> float:
    diversity = 0.0
    if record.news.source.casefold() not in seen_sources:
        diversity += 0.18
    if record.news.category.value not in seen_categories:
        diversity += 0.12
    return _base_score(record, generated_at_utc) + diversity


def _canonical_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return None
    filtered_query = urlencode(
        tuple(
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
        )
    )
    return urlunsplit(
        ("https", parsed.netloc.lower(), parsed.path.rstrip("/"), filtered_query, "")
    )


def _estimated_openai_cost(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    # Standard short-context rates per 1M tokens, pinned to the model used by this GUI.
    if model != "gpt-6-luna":
        return 0.0
    return round((input_tokens * 0.10 + output_tokens * 0.50) / 1_000_000, 8)


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("AI news-evidence generation must use UTC")
