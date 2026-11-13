"""Explicit Qt worker boundary for bounded official-news metadata collection."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from PyQt5 import QtCore

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.adapters.news_provider import NewsProvider
from trading_ig_assistant.app.projections.common import Availability
from trading_ig_assistant.app.projections.health import HealthServiceVM
from trading_ig_assistant.app.projections.macro import MacroVM, empty_macro_projection
from trading_ig_assistant.app.projections.macro_projection import build_macro_projection
from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
from trading_ig_assistant.domain.ai_context import MarketContextSnapshot
from trading_ig_assistant.domain.context_sources import (
    NewsCollectionSnapshot,
    ProviderCollectionStatus,
)
from trading_ig_assistant.domain.market_intelligence import (
    ArticleEvidenceBundle,
    ResearchTrigger,
)
from trading_ig_assistant.persistence.repositories import MarketAIAnalysisRepository
from trading_ig_assistant.services.macro_context_service import MacroContextService
from trading_ig_assistant.services.market_intelligence_runtime import (
    MarketIntelligenceRefreshResult,
    MarketIntelligenceRuntime,
)
from trading_ig_assistant.services.news_ai_evidence_service import (
    build_article_ai_evidence_signals,
    build_news_ai_evidence_signals,
)
from trading_ig_assistant.services.news_collection_service import collect_news
from trading_ig_assistant.services.openai_context_runtime_service import (
    run_openai_market_context,
)

AIContextRunner = Callable[..., MarketContextSnapshot]


@dataclass(frozen=True)
class _AIWorkerResult:
    snapshot: MarketContextSnapshot
    evidence: ArticleEvidenceBundle | None


class _OfficialNewsWorker(QtCore.QObject):
    succeeded = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(
        self,
        providers: tuple[NewsProvider, ...],
        collected_at_utc: datetime,
        intelligence_runtime: MarketIntelligenceRuntime | None = None,
        trigger: ResearchTrigger = ResearchTrigger.MANUAL,
    ) -> None:
        super().__init__()
        self._providers = providers
        self._collected_at_utc = collected_at_utc
        self._intelligence_runtime = intelligence_runtime
        self._trigger = trigger

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            if self._intelligence_runtime is not None:
                result = self._intelligence_runtime.refresh(
                    as_of_utc=self._collected_at_utc,
                    trigger=self._trigger,
                )
                self.succeeded.emit(result)
            else:
                snapshots = tuple(
                    collect_news(provider, as_of_utc=self._collected_at_utc)
                    for provider in self._providers
                )
                self.succeeded.emit(snapshots)
        except Exception:
            self.failed.emit("macro.news_invalid_result")
        finally:
            self.finished.emit()


class _AIContextWorker(QtCore.QObject):
    succeeded = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    warning = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(
        self,
        *,
        model: str,
        api_key: SecretValue,
        max_output_tokens: int,
        macro_state: object,
        response_language: str,
        runner: AIContextRunner,
        intelligence_runtime: MarketIntelligenceRuntime | None = None,
        generated_at_utc: datetime | None = None,
        snapshots: tuple[NewsCollectionSnapshot, ...] = (),
        analysis_repository: MarketAIAnalysisRepository | None = None,
    ) -> None:
        super().__init__()
        self._model = model
        self._api_key = api_key
        self._max_output_tokens = max_output_tokens
        self._macro_state = macro_state
        self._response_language = response_language
        self._runner = runner
        self._intelligence_runtime = intelligence_runtime
        self._generated_at_utc = generated_at_utc
        self._snapshots = snapshots
        self._analysis_repository = analysis_repository

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            evidence: ArticleEvidenceBundle | None = None
            macro_state = self._macro_state
            if self._intelligence_runtime is not None and self._generated_at_utc is not None:
                try:
                    evidence = self._intelligence_runtime.prepare_ai_evidence(
                        as_of_utc=self._generated_at_utc,
                        model=self._model,
                        max_output_tokens=self._max_output_tokens,
                    )
                except ValueError:
                    evidence = None
                else:
                    signals = build_article_ai_evidence_signals(evidence)
                    macro_state = MacroContextService().build_state(
                        signals,
                        self._generated_at_utc,
                    )
            result = self._runner(
                model=self._model,
                api_key=self._api_key,
                max_output_tokens=self._max_output_tokens,
                macro_state=macro_state,
                instrument_id="GLOBAL-MARKET-CONTEXT",
                response_language=self._response_language,
            )
            self.succeeded.emit(_AIWorkerResult(result, evidence))
            if self._analysis_repository is not None:
                try:
                    self._analysis_repository.save(result, evidence)
                except Exception:
                    # Persistence is important for learning, but must never erase a valid,
                    # already obtained consultative result from the current UI session.
                    self.warning.emit("macro.ai_persistence_failed")
        except Exception:
            self.failed.emit("macro.ai_failed")
        finally:
            self.finished.emit()


class MacroContextController(QtCore.QObject):
    busy_changed = QtCore.pyqtSignal(bool)
    ai_busy_changed = QtCore.pyqtSignal(bool)
    error = QtCore.pyqtSignal(str)
    ai_failed = QtCore.pyqtSignal(str)
    ready_to_close = QtCore.pyqtSignal()

    def __init__(
        self,
        *,
        runtime: TradingRuntime,
        providers: tuple[NewsProvider, ...],
        now_provider: Callable[[], datetime] | None = None,
        openai_key_reader: Callable[[], str] | None = None,
        ai_runner: AIContextRunner = run_openai_market_context,
        intelligence_runtime: MarketIntelligenceRuntime | None = None,
        analysis_repository: MarketAIAnalysisRepository | None = None,
    ) -> None:
        super().__init__()
        self._runtime = runtime
        self._providers = providers
        self._now_provider = now_provider or (lambda: datetime.now(UTC))
        self._openai_key_reader = openai_key_reader or (lambda: "")
        self._ai_runner = ai_runner
        self._intelligence_runtime = intelligence_runtime
        self._analysis_repository = analysis_repository
        self._thread: QtCore.QThread | None = None
        self._worker: _OfficialNewsWorker | None = None
        self._ai_thread: QtCore.QThread | None = None
        self._ai_worker: _AIContextWorker | None = None
        self._closing = False
        self._latest_snapshots: tuple[NewsCollectionSnapshot, ...] | None = None
        self._latest_ai_snapshot: MarketContextSnapshot | None = None
        self._latest_intelligence: MarketIntelligenceRefreshResult | None = None
        self._latest_ai_evidence: ArticleEvidenceBundle | None = None
        self._latest_ai_preview: ArticleEvidenceBundle | None = None

    @property
    def busy(self) -> bool:
        return self._thread is not None or self._ai_thread is not None

    @property
    def openai_key_present(self) -> bool:
        return bool(self._openai_key_reader().strip())

    def set_tavily_provider(self, provider: object | None) -> None:
        if self._intelligence_runtime is not None:
            self._intelligence_runtime.set_tavily_provider(provider)

    def set_tavily_extractor(self, provider: object | None) -> None:
        if self._intelligence_runtime is not None:
            self._intelligence_runtime.set_tavily_extractor(provider)

    def set_gdelt_provider(self, provider: object | None) -> None:
        if self._intelligence_runtime is not None:
            self._intelligence_runtime.set_gdelt_provider(provider)

    @QtCore.pyqtSlot()
    def refresh_news(self) -> None:
        if self.busy:
            self.error.emit("macro.news_busy")
            return
        if not self._providers:
            self.error.emit("macro.news_no_provider")
            return
        worker = _OfficialNewsWorker(
            self._providers,
            self._now_provider(),
            self._intelligence_runtime,
            ResearchTrigger.MANUAL,
        )
        thread = QtCore.QThread(self)
        self._worker = worker
        self._thread = thread
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._on_succeeded)
        worker.failed.connect(self.error)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_finished)
        self.busy_changed.emit(True)
        thread.start()

    @QtCore.pyqtSlot(str, int, str)
    def run_ai_analysis(
        self,
        model: str,
        max_output_tokens: int,
        locale: str,
    ) -> None:
        if self.busy:
            self.error.emit("macro.ai_busy")
            return
        normalized_model = model.strip()
        response_language = "fr" if locale.lower().startswith("fr") else "en"
        if not normalized_model or not 1 <= max_output_tokens <= 2_000:
            self.error.emit("macro.ai_invalid_request")
            return
        key = self._openai_key_reader().strip()
        if not key:
            self.error.emit("macro.ai_key_missing")
            return
        snapshots = self._latest_snapshots
        if not snapshots:
            self.error.emit("macro.ai_news_required")
            return
        now = self._now_provider()
        signals = build_news_ai_evidence_signals(
            snapshots,
            generated_at_utc=now,
            valid_for=timedelta(hours=24),
            max_items=5,
        )
        if not signals:
            self.error.emit("macro.ai_news_required")
            return
        macro_state = MacroContextService().build_state(signals, now)
        worker = _AIContextWorker(
            model=normalized_model,
            api_key=SecretValue(key),
            max_output_tokens=max_output_tokens,
            macro_state=macro_state,
            response_language=response_language,
            runner=self._ai_runner,
            intelligence_runtime=self._intelligence_runtime,
            generated_at_utc=now,
            snapshots=snapshots,
            analysis_repository=self._analysis_repository,
        )
        thread = QtCore.QThread(self)
        self._ai_worker = worker
        self._ai_thread = thread
        self._runtime.publish_ai_status(
            generation_id=self._runtime.generation_id,
            status="running",
            observed_at_utc=now,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._on_ai_succeeded)
        worker.failed.connect(self._on_ai_failed)
        worker.warning.connect(self.error)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_ai_finished)
        self.ai_busy_changed.emit(True)
        thread.start()

    @QtCore.pyqtSlot(object)
    def _on_succeeded(self, value: object) -> None:
        if isinstance(value, MarketIntelligenceRefreshResult):
            self._latest_intelligence = value
            self._latest_snapshots = value.news_snapshots
            self._latest_ai_snapshot = None
            self._latest_ai_evidence = None
            self._refresh_ai_preview()
            self.publish_current()
            return
        if not isinstance(value, tuple) or any(
            not isinstance(item, NewsCollectionSnapshot) for item in value
        ):
            self.error.emit("macro.news_invalid_result")
            return
        self._latest_snapshots = value
        self._latest_ai_snapshot = None
        self._latest_ai_evidence = None
        self._refresh_ai_preview()
        self.publish_current()

    @QtCore.pyqtSlot(object)
    def _on_ai_succeeded(self, value: object) -> None:
        if not isinstance(value, _AIWorkerResult):
            self.error.emit("macro.ai_invalid_result")
            return
        self._latest_ai_snapshot = value.snapshot
        self._latest_ai_evidence = value.evidence
        self.publish_current()

    @QtCore.pyqtSlot(str)
    def _on_ai_failed(self, reason: str) -> None:
        self.error.emit(reason)
        self.ai_failed.emit(reason)

    @QtCore.pyqtSlot()
    def publish_current(self) -> None:
        now = self._now_provider()
        if self._latest_snapshots is None:
            macro = empty_macro_projection(self._runtime.generation_id, now)
        else:
            macro = build_macro_projection(
                generation_id=self._runtime.generation_id,
                snapshots=self._latest_snapshots,
                generated_at_utc=now,
                ai_snapshot=self._latest_ai_snapshot,
                ai_evidence=self._latest_ai_evidence,
                ai_preview=self._latest_ai_preview,
                intelligence_snapshot=(
                    self._latest_intelligence.intelligence
                    if self._latest_intelligence is not None
                    else None
                ),
                quota=(
                    self._latest_intelligence.quota
                    if self._latest_intelligence is not None
                    else None
                ),
                tavily_collection_status=(
                    self._latest_intelligence.tavily_status
                    if self._latest_intelligence is not None
                    else ProviderCollectionStatus.UNAVAILABLE
                ),
                gdelt_collection_status=(
                    self._latest_intelligence.gdelt_status
                    if self._latest_intelligence is not None
                    else ProviderCollectionStatus.UNAVAILABLE
                ),
            )
        self._runtime.publish_macro(macro)
        self._runtime.publish_market_context(
            generation_id=macro.generation_id,
            snapshot=self._latest_ai_snapshot,
        )
        self._runtime.publish_health_service(_news_health(macro))
        self._runtime.publish_health_service(
            _ai_health(macro, key_present=self.openai_key_present)
        )
        ai_status = (
            "ready"
            if macro.ai_status is Availability.READY
            else "stale"
            if macro.ai_status is Availability.STALE
            else "configured"
            if self.openai_key_present
            else "not_configured"
        )
        self._runtime.publish_ai_status(
            generation_id=macro.generation_id,
            status=ai_status,
            observed_at_utc=now,
        )

    def _refresh_ai_preview(self) -> None:
        self._latest_ai_preview = None
        if self._intelligence_runtime is None:
            return
        try:
            self._latest_ai_preview = self._intelligence_runtime.preview_ai_evidence(
                as_of_utc=self._now_provider(),
                model="gpt-6-luna",
                max_output_tokens=600,
            )
        except ValueError:
            pass

    def close(self) -> bool:
        if self.busy:
            self._closing = True
            return False
        return True

    @QtCore.pyqtSlot()
    def _on_finished(self) -> None:
        self._thread = None
        self._worker = None
        self.busy_changed.emit(False)
        if self._closing:
            self._closing = False
            self.ready_to_close.emit()

    @QtCore.pyqtSlot()
    def _on_ai_finished(self) -> None:
        self._ai_thread = None
        self._ai_worker = None
        self.publish_current()
        self.ai_busy_changed.emit(False)
        if self._closing and not self.busy:
            self._closing = False
            self.ready_to_close.emit()


def _news_health(snapshot: MacroVM) -> HealthServiceVM:
    return HealthServiceVM(
        generation_id=snapshot.generation_id,
        service_id="official-news",
        status=snapshot.news_status,
        summary=(
            "metadata available"
            if snapshot.news_status is Availability.READY
            else "not collected"
        ),
        observed_at_utc=snapshot.generated_at_utc,
        last_success_at_utc=(
            snapshot.generated_at_utc
            if snapshot.news_status is Availability.READY
            else None
        ),
        reason_codes=snapshot.news_reason_codes or ("OFFICIAL_NEWS_AVAILABLE",),
    )


def _ai_health(snapshot: MacroVM, *, key_present: bool) -> HealthServiceVM:
    if snapshot.ai_status is Availability.READY:
        status = Availability.READY
        summary = "last request available"
        reasons = snapshot.ai_reason_codes or ("AI_CONTEXT_AVAILABLE",)
        last_success = snapshot.ai_generated_at_utc
    elif snapshot.ai_status is Availability.STALE:
        status = Availability.STALE
        summary = "last request stale"
        reasons = ("AI_CONTEXT_EXPIRED",)
        last_success = snapshot.ai_generated_at_utc
    elif key_present:
        status = Availability.WARMING_UP
        summary = "configured"
        reasons = ("AI_MANUAL_ACTION_REQUIRED",)
        last_success = None
    else:
        status = Availability.UNAVAILABLE
        summary = "not configured"
        reasons = ("OPENAI_API_KEY_MISSING",)
        last_success = None
    return HealthServiceVM(
        generation_id=snapshot.generation_id,
        service_id="openai",
        status=status,
        summary=summary,
        observed_at_utc=snapshot.generated_at_utc,
        last_success_at_utc=last_success,
        reason_codes=reasons,
    )
