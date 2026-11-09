"""Convert traceable macro/news assessments into conservative context signals."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from trading_ig_assistant.domain.context_sources import (
    MacroEvent,
    MarketContextFlag,
    NewsItem,
    SourceUsageRights,
)
from trading_ig_assistant.domain.macro_context import ContextSeverity, ContextSignal

SourceRecord = MacroEvent | NewsItem


def normalize_context_flags(
    *,
    macro_events: Sequence[MacroEvent],
    news_items: Sequence[NewsItem],
    flags: Sequence[MarketContextFlag],
    generated_at_utc: datetime,
) -> tuple[ContextSignal, ...]:
    """Validate source lineage and project flags into downstream context signals."""

    _require_utc(generated_at_utc, "context generation")
    records = _index_records((*macro_events, *news_items), generated_at_utc)
    flag_ids: set[str] = set()
    signals: list[ContextSignal] = []
    for flag in flags:
        if flag.flag_id in flag_ids:
            raise ValueError(f"duplicate context flag ID: {flag.flag_id}")
        flag_ids.add(flag.flag_id)
        if flag.observed_at_utc > generated_at_utc:
            raise ValueError(f"context flag is future-dated: {flag.flag_id}")

        try:
            sources = tuple(records[item] for item in flag.source_record_ids)
        except KeyError as exc:
            raise ValueError(
                f"context flag references unknown source record: {exc.args[0]}"
            ) from exc
        latest_observation = max(source.observed_at_utc for source in sources)
        if flag.observed_at_utc < latest_observation:
            raise ValueError(f"context flag predates its source evidence: {flag.flag_id}")

        rights_unknown = any(source.usage_rights is SourceUsageRights.UNKNOWN for source in sources)
        severity = ContextSeverity.GRAY if rights_unknown else flag.severity
        score = None if rights_unknown else flag.score
        confidence = None if rights_unknown else flag.confidence
        summary = flag.summary
        if rights_unknown:
            summary = f"{summary} Source usage rights are unverified."

        source_names = tuple(sorted({source.source for source in sources}))
        source_urls = tuple(
            sorted({source.source_url for source in sources if source.source_url is not None})
        )
        tags = tuple(
            dict.fromkeys(
                (
                    flag.category.value,
                    *flag.tags,
                    *(f"source_record:{item}" for item in flag.source_record_ids),
                    *(f"rights:{source.usage_rights.value}" for source in sources),
                )
            )
        )
        signals.append(
            ContextSignal(
                signal_id=flag.flag_id,
                label=flag.label,
                severity=severity,
                score=score,
                summary=summary,
                source=" + ".join(source_names),
                source_url=source_urls[0] if len(source_urls) == 1 else None,
                observed_at_utc=flag.observed_at_utc,
                valid_until_utc=flag.valid_until_utc,
                confidence=confidence,
                tags=tags,
            )
        )
    return tuple(sorted(signals, key=lambda signal: signal.signal_id))


def _index_records(
    source_records: Sequence[SourceRecord],
    generated_at_utc: datetime,
) -> dict[str, SourceRecord]:
    records: dict[str, SourceRecord] = {}
    for record in source_records:
        record_id = record.event_id if isinstance(record, MacroEvent) else record.item_id
        if record_id in records:
            raise ValueError(f"duplicate context source record ID: {record_id}")
        if record.observed_at_utc > generated_at_utc:
            raise ValueError(f"context source record is future-dated: {record_id}")
        records[record_id] = record
    return records


def _require_utc(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{label} timestamp must use UTC")
