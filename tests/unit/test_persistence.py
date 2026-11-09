import sqlite3
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.journal import JournalEvent, PnlStatus
from trading_ig_assistant.persistence.repositories import (
    CorruptPaperSnapshotError,
    DuplicateJournalEventError,
    JournalEventRepository,
    PaperSessionSnapshotRepository,
    UnsafeJournalPayloadError,
)
from trading_ig_assistant.persistence.sqlite_store import (
    CURRENT_SCHEMA_VERSION,
    MigrationError,
    SQLiteStore,
    UnsupportedSchemaError,
)


def _event(event_id: str = "EVENT-1") -> JournalEvent:
    return JournalEvent(
        event_id=event_id,
        timestamp_utc=datetime(2026, 10, 22, 12, 0, tzinfo=UTC),
        event_type="TRADE_CLOSED",
        correlation_id="CORRELATION-1",
        account_ref="ACCOUNT-OPAQUE-1",
        instrument_id="CRUDE-OIL",
        payload={"source": "synthetic-test"},
        pnl_amount=Decimal("7.25"),
        pnl_currency="EUR",
        pnl_status=PnlStatus.REALIZED,
    )


def test_store_initialization_is_explicit_versioned_and_wal(tmp_path) -> None:
    database_path = tmp_path / "trading.sqlite"
    store = SQLiteStore(database_path)

    assert database_path.exists() is False
    report = store.initialize()

    assert report.previous_version == 0
    assert report.current_version == CURRENT_SCHEMA_VERSION
    assert report.migrated is True
    connection = sqlite3.connect(database_path)
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == CURRENT_SCHEMA_VERSION
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert "paper_session_snapshots" in tables
    finally:
        connection.close()


def test_journal_repository_round_trip_is_append_only_and_deduplicated(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "trading.sqlite")
    store.initialize()
    repository = JournalEventRepository(store)
    event = _event()

    repository.append(event)

    assert repository.list_events() == (event,)
    with pytest.raises(DuplicateJournalEventError):
        repository.append(event)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        with store.connection() as connection:
            connection.execute(
                "UPDATE journal_events SET event_type = 'MUTATED' WHERE event_id = ?",
                (event.event_id,),
            )
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        with store.connection() as connection:
            connection.execute(
                "DELETE FROM journal_events WHERE event_id = ?",
                (event.event_id,),
            )
    assert repository.list_events() == (event,)


def test_journal_repository_rejects_nested_secret_fields(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "trading.sqlite")
    store.initialize()
    repository = JournalEventRepository(store)
    unsafe = JournalEvent(
        event_id="EVENT-SECRET",
        timestamp_utc=datetime(2026, 10, 22, 12, 0, tzinfo=UTC),
        event_type="DIAGNOSTIC",
        correlation_id="CORRELATION-1",
        account_ref="ACCOUNT-OPAQUE-1",
        payload={"nested": {"api_key": "synthetic-secret"}},
    )

    with pytest.raises(UnsafeJournalPayloadError):
        repository.append(unsafe)

    assert repository.list_events() == ()


def test_failed_migration_restores_existing_database_backup(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "trading.sqlite"
    original = sqlite3.connect(database_path)
    try:
        original.execute("PRAGMA application_id = 4242")
        original.commit()
    finally:
        original.close()
    store = SQLiteStore(database_path)

    def fail_migration(connection) -> None:
        connection.execute("CREATE TABLE transient_data(value TEXT)")
        raise RuntimeError("synthetic migration failure")

    monkeypatch.setattr(store, "_apply_schema_v1", fail_migration)

    with pytest.raises(MigrationError) as error:
        store.initialize()

    assert error.value.backup_path is not None
    assert error.value.backup_path.exists()
    restored = sqlite3.connect(database_path)
    try:
        assert restored.execute("PRAGMA application_id").fetchone()[0] == 4242
        tables = {
            row[0]
            for row in restored.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    finally:
        restored.close()
    assert "transient_data" not in tables


def test_unversioned_database_with_user_tables_is_refused_without_mutation(tmp_path) -> None:
    database_path = tmp_path / "unknown.sqlite"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("CREATE TABLE unknown_data(value TEXT)")
        connection.execute("INSERT INTO unknown_data(value) VALUES ('preserve-me')")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(UnsupportedSchemaError):
        SQLiteStore(database_path).initialize()

    connection = sqlite3.connect(database_path)
    try:
        assert connection.execute("SELECT value FROM unknown_data").fetchone()[0] == "preserve-me"
    finally:
        connection.close()
    assert list(tmp_path.glob("*.backup-*")) == []


def test_declared_current_schema_with_missing_objects_is_rejected(tmp_path) -> None:
    database_path = tmp_path / "incomplete.sqlite"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA user_version = 1")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(MigrationError, match="migration failed"):
        SQLiteStore(database_path).initialize()


def test_version_one_database_is_backed_up_and_migrated_without_losing_journal(
    tmp_path,
) -> None:
    database_path = tmp_path / "version-one.sqlite"
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at_utc TEXT NOT NULL
            );
            CREATE TABLE journal_events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                timestamp_utc TEXT NOT NULL,
                event_type TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                account_ref TEXT NOT NULL,
                instrument_id TEXT,
                payload_json TEXT NOT NULL,
                pnl_amount TEXT,
                pnl_currency TEXT,
                pnl_status TEXT NOT NULL,
                CHECK ((pnl_amount IS NULL) = (pnl_currency IS NULL))
            );
            CREATE TRIGGER journal_events_no_update BEFORE UPDATE ON journal_events
            BEGIN SELECT RAISE(ABORT, 'journal_events is append-only'); END;
            CREATE TRIGGER journal_events_no_delete BEFORE DELETE ON journal_events
            BEGIN SELECT RAISE(ABORT, 'journal_events is append-only'); END;
            INSERT INTO schema_migrations(version, applied_at_utc)
            VALUES (1, '2026-10-22T12:00:00Z');
            INSERT INTO journal_events(
                event_id, timestamp_utc, event_type, correlation_id, account_ref,
                payload_json, pnl_status
            ) VALUES (
                'PRESERVED', '2026-10-22T12:00:00Z', 'DIAGNOSTIC', 'C-1',
                'ACCOUNT-OPAQUE-1', '{}', 'unknown'
            );
            PRAGMA user_version = 1;
            """
        )
        connection.commit()
    finally:
        connection.close()

    report = SQLiteStore(database_path).initialize()

    assert report.previous_version == 1
    assert report.current_version == CURRENT_SCHEMA_VERSION
    assert report.backup_path is not None and report.backup_path.exists()
    migrated = sqlite3.connect(database_path)
    try:
        assert migrated.execute("PRAGMA user_version").fetchone()[0] == 2
        assert migrated.execute("SELECT event_id FROM journal_events").fetchone()[0] == "PRESERVED"
        assert migrated.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall() == [(1,), (2,)]
    finally:
        migrated.close()


def test_paper_snapshot_round_trip_is_append_only_and_rejects_secrets(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "trading.sqlite")
    store.initialize()
    repository = PaperSessionSnapshotRepository(store)
    saved_at = datetime(2026, 10, 23, 15, 0, tzinfo=UTC)

    saved = repository.save(
        snapshot_id="SNAPSHOT-1",
        session_id="SESSION-1",
        saved_at_utc=saved_at,
        payload={"format_version": 1, "decimal": "12.50"},
    )

    assert repository.latest() == saved
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        with store.connection() as connection:
            connection.execute("UPDATE paper_session_snapshots SET session_id = 'MUTATED'")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        with store.connection() as connection:
            connection.execute("DELETE FROM paper_session_snapshots")
    with pytest.raises(UnsafeJournalPayloadError):
        repository.save(
            snapshot_id="SNAPSHOT-SECRET",
            session_id="SESSION-1",
            saved_at_utc=saved_at,
            payload={"nested": {"api_key": "never-store-this"}},
        )


def test_paper_snapshot_checksum_detects_tampering(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "trading.sqlite")
    store.initialize()
    repository = PaperSessionSnapshotRepository(store)
    repository.save(
        snapshot_id="SNAPSHOT-1",
        session_id="SESSION-1",
        saved_at_utc=datetime(2026, 10, 23, 15, 0, tzinfo=UTC),
        payload={"format_version": 1},
    )
    with store.connection() as connection:
        connection.execute("DROP TRIGGER paper_session_snapshots_no_update")
        connection.execute(
            "UPDATE paper_session_snapshots SET payload_json = '{\"format_version\":2}'"
        )

    with pytest.raises(CorruptPaperSnapshotError, match="checksum"):
        repository.latest()
