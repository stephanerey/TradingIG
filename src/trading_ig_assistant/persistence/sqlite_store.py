"""Explicit, versioned SQLite initialization with recoverable migrations."""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

CURRENT_SCHEMA_VERSION = 3


class StoreNotInitializedError(RuntimeError):
    """Raised when repository access is attempted before explicit initialization."""


class UnsupportedSchemaError(RuntimeError):
    """Raised when a database cannot be migrated without an explicit design."""


class MigrationError(RuntimeError):
    """Raised after a failed migration has been rolled back or restored."""

    def __init__(self, message: str, backup_path: Path | None) -> None:
        super().__init__(message)
        self.backup_path = backup_path


@dataclass(frozen=True)
class MigrationReport:
    previous_version: int
    current_version: int
    migrated: bool
    backup_path: Path | None = None


_SCHEMA_V1_STATEMENTS = (
    """
    CREATE TABLE schema_migrations (
        version INTEGER PRIMARY KEY,
        applied_at_utc TEXT NOT NULL
    )
    """,
    """
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
        pnl_status TEXT NOT NULL CHECK (
            pnl_status IN ('realized', 'unrealized', 'estimated', 'unknown')
        ),
        CHECK ((pnl_amount IS NULL) = (pnl_currency IS NULL))
    )
    """,
    """
    CREATE TRIGGER journal_events_no_update
    BEFORE UPDATE ON journal_events
    BEGIN
        SELECT RAISE(ABORT, 'journal_events is append-only');
    END
    """,
    """
    CREATE TRIGGER journal_events_no_delete
    BEFORE DELETE ON journal_events
    BEGIN
        SELECT RAISE(ABORT, 'journal_events is append-only');
    END
    """,
)

_SCHEMA_V2_STATEMENTS = (
    """
    CREATE TABLE paper_session_snapshots (
        sequence INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_id TEXT NOT NULL UNIQUE,
        session_id TEXT NOT NULL,
        saved_at_utc TEXT NOT NULL,
        format_version INTEGER NOT NULL CHECK (format_version = 1),
        payload_json TEXT NOT NULL,
        payload_sha256 TEXT NOT NULL CHECK (length(payload_sha256) = 64)
    )
    """,
    """
    CREATE TRIGGER paper_session_snapshots_no_update
    BEFORE UPDATE ON paper_session_snapshots
    BEGIN
        SELECT RAISE(ABORT, 'paper_session_snapshots is append-only');
    END
    """,
    """
    CREATE TRIGGER paper_session_snapshots_no_delete
    BEFORE DELETE ON paper_session_snapshots
    BEGIN
        SELECT RAISE(ABORT, 'paper_session_snapshots is append-only');
    END
    """,
)

_SCHEMA_V3_STATEMENTS = (
    """
    CREATE TABLE market_ai_analyses (
        sequence INTEGER PRIMARY KEY AUTOINCREMENT,
        analysis_id TEXT NOT NULL UNIQUE,
        generated_at_utc TEXT NOT NULL,
        valid_until_utc TEXT NOT NULL,
        model_id TEXT NOT NULL,
        prompt_version TEXT NOT NULL,
        market_scope TEXT NOT NULL,
        analysis_json TEXT NOT NULL,
        source_refs_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE market_facts (
        sequence INTEGER PRIMARY KEY AUTOINCREMENT,
        fact_id TEXT NOT NULL UNIQUE,
        analysis_id TEXT NOT NULL,
        observed_at_utc TEXT NOT NULL,
        valid_until_utc TEXT NOT NULL,
        category TEXT NOT NULL,
        statement TEXT NOT NULL,
        source_refs_json TEXT NOT NULL,
        FOREIGN KEY(analysis_id) REFERENCES market_ai_analyses(analysis_id)
    )
    """,
    """
    CREATE TRIGGER market_ai_analyses_no_update
    BEFORE UPDATE ON market_ai_analyses
    BEGIN
        SELECT RAISE(ABORT, 'market_ai_analyses is append-only');
    END
    """,
    """
    CREATE TRIGGER market_ai_analyses_no_delete
    BEFORE DELETE ON market_ai_analyses
    BEGIN
        SELECT RAISE(ABORT, 'market_ai_analyses is append-only');
    END
    """,
    """
    CREATE TRIGGER market_facts_no_update
    BEFORE UPDATE ON market_facts
    BEGIN
        SELECT RAISE(ABORT, 'market_facts is append-only');
    END
    """,
    """
    CREATE TRIGGER market_facts_no_delete
    BEFORE DELETE ON market_facts
    BEGIN
        SELECT RAISE(ABORT, 'market_facts is append-only');
    END
    """,
)


class SQLiteStore:
    """Local store that performs no I/O until ``initialize`` or ``connection``."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def initialize(self) -> MigrationReport:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists() and self.path.stat().st_size > 0
        inspection = sqlite3.connect(self.path)
        try:
            previous_version = int(inspection.execute("PRAGMA user_version").fetchone()[0])
            user_tables = {
                str(row[0])
                for row in inspection.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                )
            }
        finally:
            inspection.close()

        if previous_version > CURRENT_SCHEMA_VERSION:
            raise UnsupportedSchemaError(
                f"Database schema {previous_version} is newer than supported "
                f"schema {CURRENT_SCHEMA_VERSION}."
            )
        if previous_version == 0 and user_tables:
            raise UnsupportedSchemaError(
                "Refusing to migrate an unversioned database containing user tables."
            )
        if previous_version == CURRENT_SCHEMA_VERSION:
            self._validate_integrity()
            self._validate_schema()
            self._enable_wal()
            return MigrationReport(previous_version, CURRENT_SCHEMA_VERSION, False)

        backup_path = self._create_backup() if existed else None
        connection = sqlite3.connect(self.path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            if previous_version == 0:
                self._apply_schema_v1(connection)
            if previous_version <= 1:
                self._apply_schema_v2(connection)
            if previous_version <= 2:
                self._apply_schema_v3(connection)
            connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION}")
            connection.commit()
        except Exception as exc:
            connection.rollback()
            connection.close()
            if backup_path is not None:
                shutil.copy2(backup_path, self.path)
            raise MigrationError(
                "SQLite migration failed; the previous database was restored."
                if backup_path is not None
                else "SQLite initialization failed; no previous database existed.",
                backup_path,
            ) from exc
        finally:
            if connection:
                connection.close()

        try:
            self._validate_integrity()
            self._validate_schema()
            self._enable_wal()
        except Exception as exc:
            if backup_path is not None:
                shutil.copy2(backup_path, self.path)
            raise MigrationError(
                "SQLite integrity validation failed; the previous database was restored.",
                backup_path,
            ) from exc
        return MigrationReport(
            previous_version=previous_version,
            current_version=CURRENT_SCHEMA_VERSION,
            migrated=True,
            backup_path=backup_path,
        )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        if not self.path.exists():
            raise StoreNotInitializedError("SQLite store has not been initialized.")
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version != CURRENT_SCHEMA_VERSION:
                raise StoreNotInitializedError(
                    f"SQLite schema {version} is not initialized for version "
                    f"{CURRENT_SCHEMA_VERSION}."
                )
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _apply_schema_v1(self, connection: sqlite3.Connection) -> None:
        for statement in _SCHEMA_V1_STATEMENTS:
            connection.execute(statement)
        connection.execute(
            "INSERT INTO schema_migrations(version, applied_at_utc) VALUES (?, ?)",
            (1, _utc_now_text()),
        )

    def _apply_schema_v2(self, connection: sqlite3.Connection) -> None:
        for statement in _SCHEMA_V2_STATEMENTS:
            connection.execute(statement)
        connection.execute(
            "INSERT INTO schema_migrations(version, applied_at_utc) VALUES (?, ?)",
            (2, _utc_now_text()),
        )

    def _apply_schema_v3(self, connection: sqlite3.Connection) -> None:
        for statement in _SCHEMA_V3_STATEMENTS:
            connection.execute(statement)
        connection.execute(
            "INSERT INTO schema_migrations(version, applied_at_utc) VALUES (?, ?)",
            (3, _utc_now_text()),
        )

    def _create_backup(self) -> Path:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        backup_path = self.path.with_name(f"{self.path.name}.backup-{timestamp}")
        shutil.copy2(self.path, backup_path)
        return backup_path

    def _validate_integrity(self) -> None:
        connection = sqlite3.connect(self.path)
        try:
            result = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        finally:
            connection.close()
        if result.lower() != "ok":
            raise MigrationError("SQLite integrity check failed.", None)

    def _enable_wal(self) -> None:
        connection = sqlite3.connect(self.path)
        try:
            mode = str(connection.execute("PRAGMA journal_mode = WAL").fetchone()[0])
        finally:
            connection.close()
        if mode.lower() != "wal":
            raise MigrationError("SQLite WAL mode could not be enabled.", None)

    def _validate_schema(self) -> None:
        connection = sqlite3.connect(self.path)
        try:
            tables = {
                str(row[0])
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
            triggers = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'trigger'"
                )
            }
            migration = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        except sqlite3.DatabaseError as exc:
            raise MigrationError("SQLite schema validation failed.", None) from exc
        finally:
            connection.close()
        required_tables = {
            "schema_migrations",
            "journal_events",
            "paper_session_snapshots",
            "market_ai_analyses",
            "market_facts",
        }
        required_triggers = {
            "journal_events_no_update",
            "journal_events_no_delete",
            "paper_session_snapshots_no_update",
            "paper_session_snapshots_no_delete",
            "market_ai_analyses_no_update",
            "market_ai_analyses_no_delete",
            "market_facts_no_update",
            "market_facts_no_delete",
        }
        if not required_tables.issubset(tables) or not required_triggers.issubset(triggers):
            raise MigrationError("SQLite schema objects are incomplete.", None)
        if migration is None or migration[0] != CURRENT_SCHEMA_VERSION:
            raise MigrationError("SQLite migration history is inconsistent.", None)


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
