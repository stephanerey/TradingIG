"""Repositories over the explicit local SQLite store."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any

from trading_ig_assistant.domain.ai_context import MarketContextSnapshot
from trading_ig_assistant.domain.journal import JournalEvent, PnlStatus
from trading_ig_assistant.domain.market_intelligence import ArticleEvidenceBundle
from trading_ig_assistant.persistence.sqlite_store import SQLiteStore
from trading_ig_assistant.utils.redaction import is_secret_key


class DuplicateJournalEventError(RuntimeError):
    """Raised when an immutable event ID is appended twice."""


class UnsafeJournalPayloadError(ValueError):
    """Raised when a payload contains authentication material."""


class CorruptPaperSnapshotError(ValueError):
    """Raised when a persisted Paper checkpoint fails validation."""


class MarketAIAnalysisRepository:
    """Persist only structured analysis/facts and source references, never excerpts."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def save(
        self,
        snapshot: MarketContextSnapshot,
        evidence: ArticleEvidenceBundle | None,
    ) -> None:
        self._store.initialize()
        analysis = snapshot.ai_analysis
        source_by_id = {
            article.signal_id: {
                "signal_id": article.signal_id,
                "headline": article.headline,
                "source": article.source,
                "source_url": article.source_url,
                "published_at_utc": _utc_text(article.published_at_utc),
                "content_origin": article.content_origin.value,
            }
            for article in evidence.articles
        } if evidence is not None else {}
        source_refs = tuple(
            source_by_id.get(source_id, {"signal_id": source_id})
            for source_id in analysis.source_signal_ids
        )
        analysis_payload = {
            "status": analysis.status.value,
            "directional_bias": analysis.directional_bias.value,
            "event_risk": analysis.event_risk.value,
            "confidence": str(analysis.confidence) if analysis.confidence is not None else None,
            "summary": analysis.summary,
            "risk_flags": analysis.risk_flags,
            "source_signal_ids": analysis.source_signal_ids,
        }
        analysis_json = json.dumps(analysis_payload, ensure_ascii=False, separators=(",", ":"))
        source_refs_json = json.dumps(source_refs, ensure_ascii=False, separators=(",", ":"))
        with self._store.connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO market_ai_analyses(
                    analysis_id, generated_at_utc, valid_until_utc, model_id,
                    prompt_version, market_scope, analysis_json, source_refs_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.snapshot_id,
                    _utc_text(analysis.generated_at_utc),
                    _utc_text(analysis.valid_until_utc),
                    analysis.model_id,
                    analysis.prompt_version,
                    analysis.market_scope,
                    analysis_json,
                    source_refs_json,
                ),
            )
            for index, fact in enumerate(analysis.facts):
                fact_sources = tuple(
                    source_by_id.get(source_id, {"signal_id": source_id})
                    for source_id in fact.source_signal_ids
                )
                fact_material = (
                    f"{snapshot.snapshot_id}:{index}:{fact.category}:{fact.statement}"
                )
                fact_id = sha256(fact_material.encode("utf-8")).hexdigest()
                connection.execute(
                    """
                    INSERT OR IGNORE INTO market_facts(
                        fact_id, analysis_id, observed_at_utc, valid_until_utc,
                        category, statement, source_refs_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fact_id,
                        snapshot.snapshot_id,
                        _utc_text(fact.observed_at_utc),
                        _utc_text(fact.valid_until_utc),
                        fact.category,
                        fact.statement,
                        json.dumps(fact_sources, ensure_ascii=False, separators=(",", ":")),
                    ),
                )


@dataclass(frozen=True)
class PaperSessionSnapshotRecord:
    snapshot_id: str
    session_id: str
    saved_at_utc: datetime
    payload: dict[str, Any]
    payload_sha256: str


class PaperSessionSnapshotRepository:
    FORMAT_VERSION = 1

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def save(
        self,
        *,
        snapshot_id: str,
        session_id: str,
        saved_at_utc: datetime,
        payload: dict[str, Any],
    ) -> PaperSessionSnapshotRecord:
        if not snapshot_id.strip() or not session_id.strip():
            raise ValueError("Paper snapshot and session identifiers are required.")
        if saved_at_utc.tzinfo is None or saved_at_utc.utcoffset().total_seconds() != 0:
            raise ValueError("Paper snapshot timestamp must use UTC.")
        _reject_secret_keys(payload)
        try:
            payload_json = json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("Paper snapshot payload must be valid JSON data.") from exc
        digest = sha256(payload_json.encode("utf-8")).hexdigest()
        with self._store.connection() as connection:
            connection.execute(
                """
                INSERT INTO paper_session_snapshots(
                    snapshot_id, session_id, saved_at_utc, format_version,
                    payload_json, payload_sha256
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    session_id,
                    saved_at_utc.isoformat().replace("+00:00", "Z"),
                    self.FORMAT_VERSION,
                    payload_json,
                    digest,
                ),
            )
        return PaperSessionSnapshotRecord(
            snapshot_id=snapshot_id,
            session_id=session_id,
            saved_at_utc=saved_at_utc,
            payload=payload,
            payload_sha256=digest,
        )

    def latest(self) -> PaperSessionSnapshotRecord | None:
        with self._store.connection() as connection:
            row = connection.execute(
                """
                SELECT snapshot_id, session_id, saved_at_utc, format_version,
                       payload_json, payload_sha256
                FROM paper_session_snapshots
                ORDER BY sequence DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        if int(row["format_version"]) != self.FORMAT_VERSION:
            raise CorruptPaperSnapshotError("Unsupported Paper snapshot format version.")
        payload_json = str(row["payload_json"])
        expected_digest = str(row["payload_sha256"])
        actual_digest = sha256(payload_json.encode("utf-8")).hexdigest()
        if actual_digest != expected_digest:
            raise CorruptPaperSnapshotError("Paper snapshot checksum mismatch.")
        try:
            payload = json.loads(payload_json)
        except (TypeError, ValueError) as exc:
            raise CorruptPaperSnapshotError("Paper snapshot JSON is invalid.") from exc
        if not isinstance(payload, dict):
            raise CorruptPaperSnapshotError("Paper snapshot payload must be an object.")
        _reject_secret_keys(payload)
        saved_at_utc = datetime.fromisoformat(str(row["saved_at_utc"]).replace("Z", "+00:00"))
        if saved_at_utc.utcoffset() is None or saved_at_utc.utcoffset().total_seconds() != 0:
            raise CorruptPaperSnapshotError("Paper snapshot timestamp is not UTC.")
        return PaperSessionSnapshotRecord(
            snapshot_id=str(row["snapshot_id"]),
            session_id=str(row["session_id"]),
            saved_at_utc=saved_at_utc,
            payload=payload,
            payload_sha256=expected_digest,
        )


class JournalEventRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def append(self, event: JournalEvent) -> None:
        values = _journal_event_values(event)
        try:
            with self._store.connection() as connection:
                connection.execute(
                    """
                    INSERT INTO journal_events(
                        event_id, timestamp_utc, event_type, correlation_id,
                        account_ref, instrument_id, payload_json, pnl_amount,
                        pnl_currency, pnl_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
        except sqlite3.IntegrityError as exc:
            if "event_id" in str(exc).lower() or "unique" in str(exc).lower():
                raise DuplicateJournalEventError(
                    f"Journal event {event.event_id!r} already exists."
                ) from exc
            raise

    def append_many(self, events: tuple[JournalEvent, ...]) -> None:
        """Append a validated batch atomically without weakening event immutability."""

        if not events:
            return
        event_ids = tuple(event.event_id for event in events)
        if len(set(event_ids)) != len(event_ids):
            raise DuplicateJournalEventError("Journal batch contains duplicate event IDs.")
        rows = tuple(_journal_event_values(event) for event in events)
        try:
            with self._store.connection() as connection:
                connection.executemany(
                    """
                    INSERT INTO journal_events(
                        event_id, timestamp_utc, event_type, correlation_id,
                        account_ref, instrument_id, payload_json, pnl_amount,
                        pnl_currency, pnl_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
        except sqlite3.IntegrityError as exc:
            if "event_id" in str(exc).lower() or "unique" in str(exc).lower():
                raise DuplicateJournalEventError(
                    "One or more immutable journal events already exist."
                ) from exc
            raise

    def existing_event_ids(self, event_ids: tuple[str, ...]) -> frozenset[str]:
        """Return immutable event IDs already present, using bound parameters only."""

        unique_ids = tuple(dict.fromkeys(event_id for event_id in event_ids if event_id))
        if not unique_ids:
            return frozenset()
        placeholders = ",".join("?" for _event_id in unique_ids)
        with self._store.connection() as connection:
            rows = connection.execute(
                f"SELECT event_id FROM journal_events WHERE event_id IN ({placeholders})",
                unique_ids,
            ).fetchall()
        return frozenset(str(row["event_id"]) for row in rows)

    def list_events(self) -> tuple[JournalEvent, ...]:
        with self._store.connection() as connection:
            rows = connection.execute(
                """
                SELECT event_id, timestamp_utc, event_type, correlation_id,
                       account_ref, instrument_id, payload_json, pnl_amount,
                       pnl_currency, pnl_status
                FROM journal_events
                ORDER BY sequence
                """
            ).fetchall()
        return tuple(_event_from_row(row) for row in rows)


def _event_from_row(row: sqlite3.Row) -> JournalEvent:
    timestamp = datetime.fromisoformat(str(row["timestamp_utc"]).replace("Z", "+00:00"))
    amount = row["pnl_amount"]
    return JournalEvent(
        event_id=str(row["event_id"]),
        timestamp_utc=timestamp,
        event_type=str(row["event_type"]),
        correlation_id=str(row["correlation_id"]),
        account_ref=str(row["account_ref"]),
        instrument_id=str(row["instrument_id"]) if row["instrument_id"] is not None else None,
        payload=json.loads(str(row["payload_json"])),
        pnl_amount=Decimal(str(amount)) if amount is not None else None,
        pnl_currency=(str(row["pnl_currency"]) if row["pnl_currency"] is not None else None),
        pnl_status=PnlStatus(str(row["pnl_status"])),
    )


def _journal_event_values(event: JournalEvent) -> tuple[Any, ...]:
    _reject_secret_keys(event.payload)
    try:
        payload_json = json.dumps(
            event.payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Journal payload must be valid JSON data.") from exc
    return (
        event.event_id,
        event.timestamp_text(),
        event.event_type,
        event.correlation_id,
        event.account_ref,
        event.instrument_id,
        payload_json,
        str(event.pnl_amount) if event.pnl_amount is not None else None,
        event.pnl_currency,
        event.pnl_status.value,
    )


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset().total_seconds() != 0:
        raise ValueError("Persisted AI timestamps must use UTC.")
    return value.isoformat().replace("+00:00", "Z")


def _reject_secret_keys(value: Any, path: str = "payload") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if is_secret_key(key_text):
                raise UnsafeJournalPayloadError(
                    f"Journal payload contains forbidden secret field at {path}.{key_text}."
                )
            _reject_secret_keys(child, f"{path}.{key_text}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_secret_keys(child, f"{path}[{index}]")
