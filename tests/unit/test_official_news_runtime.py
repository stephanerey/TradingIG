import threading
import time
from datetime import UTC, datetime, timedelta

from trading_ig_assistant.domain.context_sources import (
    NewsCollectionSnapshot,
    ProviderCollectionStatus,
)
from trading_ig_assistant.domain.macro_context import ContextSeverity
from trading_ig_assistant.services.news_context_health_service import (
    build_news_source_health_signal,
)

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


def _snapshot(
    provider_id: str,
    status: ProviderCollectionStatus,
) -> NewsCollectionSnapshot:
    return NewsCollectionSnapshot(
        schema_version=1,
        provider_id=provider_id,
        status=status,
        items=(),
        collected_at_utc=NOW,
        reason_codes=()
        if status is ProviderCollectionStatus.AVAILABLE
        else ("NEWS_PROVIDER_ERROR",),
    )


def test_official_news_health_is_non_directional_and_explicit() -> None:
    signal = build_news_source_health_signal(
        (
            _snapshot("fed", ProviderCollectionStatus.AVAILABLE),
            _snapshot("ecb", ProviderCollectionStatus.UNAVAILABLE),
        ),
        generated_at_utc=NOW,
        valid_for=timedelta(minutes=15),
    )

    assert signal.severity is ContextSeverity.YELLOW
    assert signal.score is None
    assert signal.confidence is None
    assert signal.tags == ("data_health", "official_news")
    assert "1/2" in signal.summary
    assert "ecb" in signal.summary


def test_all_unavailable_official_news_health_stays_gray() -> None:
    signal = build_news_source_health_signal(
        (
            _snapshot("fed", ProviderCollectionStatus.UNAVAILABLE),
            _snapshot("ecb", ProviderCollectionStatus.UNAVAILABLE),
        ),
        generated_at_utc=NOW,
        valid_for=timedelta(minutes=15),
    )

    assert signal.severity is ContextSeverity.GRAY
    assert signal.score is None


def test_source_health_expires_from_collection_not_rebuild() -> None:
    collection = _snapshot("fed", ProviderCollectionStatus.AVAILABLE)
    signal = build_news_source_health_signal(
        (collection,), generated_at_utc=NOW + timedelta(minutes=10), valid_for=timedelta(minutes=15)
    )
    assert signal.severity is ContextSeverity.GREEN
    assert signal.valid_until_utc == NOW + timedelta(minutes=15)

    expired = build_news_source_health_signal(
        (collection,), generated_at_utc=NOW + timedelta(minutes=15), valid_for=timedelta(minutes=15)
    )
    assert expired.severity is ContextSeverity.GRAY
    assert "fed" in expired.summary
    assert "Stale" in expired.summary


def test_refresh_start_degrades_expired_source_even_without_network() -> None:
    from dataclasses import replace

    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    window = MainWindow()
    old_time = datetime.now(UTC) - timedelta(minutes=20)
    window._latest_news_snapshots = (
        replace(_snapshot("fed", ProviderCollectionStatus.AVAILABLE), collected_at_utc=old_time),
    )
    window._refresh_official_news()
    health = next(
        signal
        for signal in window._latest_macro_state.signals
        if signal.signal_id == "official-news-source-health"
    )
    assert health.severity is ContextSeverity.GRAY
    assert "Stale" in health.summary
    assert window._official_news_thread is None
    window.close()


def test_official_news_worker_does_not_block_qt_event_loop() -> None:
    from PyQt5 import QtCore, QtWidgets

    from trading_ig_assistant.ui.official_news_refresh import OfficialNewsRefreshWorker

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    started = threading.Event()
    release = threading.Event()

    class SlowProvider:
        provider_id = "slow-official-provider"

        def fetch_news(self, *, as_of_utc):
            assert as_of_utc.tzinfo is UTC
            started.set()
            assert release.wait(2.0)
            return ()

    thread = QtCore.QThread()
    worker = OfficialNewsRefreshWorker((SlowProvider(),))
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    thread.start()
    assert started.wait(1.0)

    timer_fired: list[bool] = []
    QtCore.QTimer.singleShot(0, lambda: timer_fired.append(True))
    app.processEvents()
    assert timer_fired == [True]

    release.set()
    deadline = time.monotonic() + 2.0
    while thread.isRunning() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert thread.wait(1000)


def test_main_window_projects_injected_official_source_health() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    class AvailableProvider:
        provider_id = "offline-official-provider"

        def fetch_news(self, *, as_of_utc):
            assert as_of_utc.tzinfo is UTC
            return ()

    window = MainWindow(
        official_news_providers=(AvailableProvider(),),
        official_news_refresh_interval_ms=60_000,
    )
    deadline = time.monotonic() + 2.0
    while (
        window._official_news_thread is not None
        or not any("Official news sources" in label.text() for label in window.macro_ribbon._labels)
    ) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)

    labels = [label.text() for label in window.macro_ribbon._labels]
    assert "Official news sources: green [GREEN]" in labels
    assert "unknown" in labels[0]
    window.close()
