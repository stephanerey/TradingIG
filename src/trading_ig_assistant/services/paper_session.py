"""Volatile application session for risk-gated Paper positions and audit views."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from threading import RLock
from uuid import uuid4

from trading_ig_assistant.domain.adapter_contracts import (
    AccountRef,
    ExecutionResult,
    ExecutionStatus,
)
from trading_ig_assistant.domain.journal import JournalEvent, PnlStatus
from trading_ig_assistant.domain.market_data import QUOTE_FRESHNESS_SECONDS, Quote
from trading_ig_assistant.domain.positions import (
    PaperFillAssumptions,
    PaperPosition,
    PaperPositionStatus,
    PaperQuote,
)
from trading_ig_assistant.domain.risk import (
    ExposureState,
    PortfolioRiskSnapshot,
    ResolvedRiskSettings,
    RiskRequest,
)
from trading_ig_assistant.domain.tickets import TicketDraft
from trading_ig_assistant.services.order_execution_coordinator import (
    PaperExecutionOutcome,
    PaperOrderExecutionCoordinator,
)
from trading_ig_assistant.services.paper_broker import PaperBroker
from trading_ig_assistant.services.risk_engine import RiskEngine

LOCAL_PAPER_ACCOUNT = AccountRef(
    broker_id="paper",
    environment="paper",
    account_id="local-paper-preview",
)


@dataclass(frozen=True)
class PaperTicketSubmission:
    ticket: TicketDraft
    risk_request: RiskRequest
    risk_snapshot: PortfolioRiskSnapshot
    risk_settings: ResolvedRiskSettings
    quote: PaperQuote
    assumptions: PaperFillAssumptions

    def __post_init__(self) -> None:
        intent = self.ticket.intent
        if intent.account != LOCAL_PAPER_ACCOUNT:
            raise ValueError("Paper GUI submissions require the local Paper account")
        if self.risk_request.intent_id != intent.intent_id:
            raise ValueError("Paper submission risk request must match the ticket intent")
        if self.risk_request.account != intent.account:
            raise ValueError("Paper submission risk account must match the ticket intent")
        if self.quote.product_id != intent.product_id:
            raise ValueError("Paper submission quote must match the ticket product")


@dataclass(frozen=True)
class PaperOrderRecord:
    submission: PaperTicketSubmission
    outcome: PaperExecutionOutcome
    submitted_at_utc: datetime


@dataclass(frozen=True)
class PaperPositionSnapshot:
    position: PaperPosition
    mark_price: Decimal | None
    net_pnl: Decimal | None


@dataclass(frozen=True)
class PaperSessionState:
    session_id: str
    orders: tuple[PaperOrderRecord, ...]
    positions: tuple[PaperPosition, ...]
    events: tuple[JournalEvent, ...]
    latest_quotes: tuple[tuple[str, PaperQuote], ...]
    assumptions: tuple[tuple[str, PaperFillAssumptions], ...]
    currencies: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not self.session_id.strip():
            raise ValueError("Paper session ID is required")


class PaperSessionService:
    """Own one in-memory Paper boundary; it cannot route to an IG adapter."""

    def __init__(
        self,
        *,
        now_provider: Callable[[], datetime] | None = None,
        session_id: str | None = None,
    ) -> None:
        self._now_provider = now_provider or (lambda: datetime.now(UTC))
        self.session_id = session_id or f"paper-session-{uuid4().hex}"
        self._risk_engine = RiskEngine()
        self._broker = PaperBroker((LOCAL_PAPER_ACCOUNT,))
        self._coordinator = PaperOrderExecutionCoordinator(self._risk_engine, self._broker)
        self._submissions: dict[str, PaperTicketSubmission] = {}
        self._orders: dict[str, PaperOrderRecord] = {}
        self._journal: list[JournalEvent] = []
        self._latest_quotes: dict[str, PaperQuote] = {}
        self._assumptions: dict[str, PaperFillAssumptions] = {}
        self._currencies: dict[str, str] = {}
        self._event_sequence = 0
        self._lock = RLock()

    def submit(self, submission: PaperTicketSubmission) -> PaperOrderRecord:
        intent = submission.ticket.intent
        with self._lock:
            existing = self._orders.get(intent.intent_id)
            if existing is not None:
                if self._submissions[intent.intent_id] != submission:
                    raise ValueError("intent_id already submitted with different Paper content")
                return existing

            self._submissions[intent.intent_id] = submission
            self._assumptions[intent.intent_id] = submission.assumptions
            self._currencies[intent.product_id] = submission.quote.currency
            self._latest_quotes[intent.product_id] = submission.quote
            self._append_session_event(
                submission.quote.observed_at_utc,
                "PAPER_PROPOSAL_SUBMITTED",
                intent.intent_id,
                intent.product_id,
                {
                    "direction": intent.direction.value,
                    "quantity": str(intent.quantity),
                    "simulation_only": True,
                },
            )
            before_event_count = len(self._broker.events())
            self._broker.publish_quote(submission.quote)
            outcome = self._coordinator.execute(
                intent,
                submission.risk_request,
                submission.risk_snapshot,
                assumptions=submission.assumptions,
                settings=submission.risk_settings,
            )
            self._append_new_broker_events(before_event_count)
            if outcome.execution_result.status is not ExecutionStatus.CONFIRMED:
                self._append_session_event(
                    submission.quote.observed_at_utc,
                    "PAPER_EXECUTION_REJECTED",
                    intent.intent_id,
                    intent.product_id,
                    {"reason": outcome.execution_result.message or "UNKNOWN"},
                )
            record = PaperOrderRecord(
                submission=submission,
                outcome=outcome,
                submitted_at_utc=submission.quote.observed_at_utc,
            )
            self._orders[intent.intent_id] = record
            return record

    def process_market_quote(
        self,
        quote: Quote,
        *,
        observed_at_utc: datetime,
    ) -> tuple[ExecutionResult, ...]:
        with self._lock:
            currency = self._currencies.get(quote.epic)
            if currency is None or quote.bid is None or quote.offer is None:
                return ()
            paper_quote = PaperQuote(
                product_id=quote.epic,
                observed_at_utc=observed_at_utc,
                bid=Decimal(str(quote.bid)),
                ask=Decimal(str(quote.offer)),
                currency=currency,
                fresh=quote.delayed is not True,
                market_open=(quote.market_state or "").upper() == "TRADEABLE",
                product_supported=True,
                provenance="gui-stream-quote",
            )
            before_event_count = len(self._broker.events())
            results = self._coordinator.process_quote(paper_quote)
            self._latest_quotes[quote.epic] = paper_quote
            self._append_new_broker_events(before_event_count)
            return results

    def move_stop(self, position_id: str, stop: Decimal) -> ExecutionResult:
        """Request one local Paper stop update; widening remains broker-forbidden."""

        with self._lock:
            position = self._position_by_id(position_id)
            before_event_count = len(self._broker.events())
            result = self._broker.move_stop(LOCAL_PAPER_ACCOUNT, position_id, stop)
            self._append_new_broker_events(before_event_count)
            if result.status is not ExecutionStatus.CONFIRMED:
                self._append_action_rejection(
                    "PAPER_STOP_UPDATE_REJECTED",
                    position_id,
                    position,
                    {"reason": result.message or "UNKNOWN", "requested_stop": str(stop)},
                )
            return result

    def close_position(self, position_id: str) -> ExecutionResult:
        """Close one local Paper position at the latest simulated executable quote."""

        with self._lock:
            position = self._position_by_id(position_id)
            before_event_count = len(self._broker.events())
            if position is not None and not self._quote_is_current(
                self._latest_quotes.get(position.product_id)
            ):
                result = ExecutionResult(
                    intent_id=position_id,
                    account=LOCAL_PAPER_ACCOUNT,
                    status=ExecutionStatus.REJECTED,
                    broker_reference=position_id,
                    message="STALE_PRICE",
                )
            else:
                result = self._coordinator.close(LOCAL_PAPER_ACCOUNT, position_id)
            self._append_new_broker_events(before_event_count)
            if result.status is not ExecutionStatus.CONFIRMED:
                self._append_action_rejection(
                    "PAPER_MANUAL_CLOSE_REJECTED",
                    position_id,
                    position,
                    {"reason": result.message or "UNKNOWN"},
                )
            return result

    def open_exposures(self) -> tuple[ExposureState, ...]:
        with self._lock:
            return tuple(
                ExposureState(
                    exposure_id=position.position_id,
                    account=position.account,
                    underlying_id=position.underlying_id,
                    origin_intent_id=position.intent_id,
                )
                for position in self._broker.positions(LOCAL_PAPER_ACCOUNT)
                if position.status is PaperPositionStatus.OPEN
            )

    def tracks_product(self, product_id: str) -> bool:
        with self._lock:
            return product_id in self._currencies

    def invalidate_market_quotes(self) -> None:
        """Invalidate session marks without generating fills when the source disconnects."""
        with self._lock:
            for product_id, quote in tuple(self._latest_quotes.items()):
                stale = replace(quote, fresh=False)
                self._broker.publish_quote(stale)
                self._latest_quotes[product_id] = stale

    def position_snapshots(self) -> tuple[PaperPositionSnapshot, ...]:
        with self._lock:
            return tuple(
                self._position_snapshot(position)
                for position in self._broker.positions(LOCAL_PAPER_ACCOUNT)
            )

    def orders(self) -> tuple[PaperOrderRecord, ...]:
        with self._lock:
            return tuple(self._orders.values())

    def events(self) -> tuple[JournalEvent, ...]:
        with self._lock:
            return tuple(self._journal)

    def has_state(self) -> bool:
        with self._lock:
            return bool(
                self._orders or self._journal or self._broker.positions(LOCAL_PAPER_ACCOUNT)
            )

    def checkpoint_state(self) -> PaperSessionState:
        with self._lock:
            return PaperSessionState(
                session_id=self.session_id,
                orders=tuple(self._orders.values()),
                positions=self._broker.positions(LOCAL_PAPER_ACCOUNT),
                events=tuple(self._journal),
                latest_quotes=tuple(self._latest_quotes.items()),
                assumptions=tuple(self._assumptions.items()),
                currencies=tuple(self._currencies.items()),
            )

    @classmethod
    def from_checkpoint_state(
        cls,
        state: PaperSessionState,
        *,
        now_provider: Callable[[], datetime] | None = None,
    ) -> PaperSessionService:
        service = cls(now_provider=now_provider, session_id=state.session_id)
        order_ids = [record.submission.ticket.intent.intent_id for record in state.orders]
        if len(set(order_ids)) != len(order_ids):
            raise ValueError("Paper checkpoint contains duplicate orders")
        positions_by_intent = {position.intent_id: position for position in state.positions}
        if len(positions_by_intent) != len(state.positions):
            raise ValueError("Paper checkpoint contains duplicate position intents")
        quote_map = dict(state.latest_quotes)
        assumption_map = dict(state.assumptions)
        currency_map = dict(state.currencies)
        if len(quote_map) != len(state.latest_quotes):
            raise ValueError("Paper checkpoint contains duplicate quote products")
        if len(assumption_map) != len(state.assumptions):
            raise ValueError("Paper checkpoint contains duplicate assumptions")
        if len(currency_map) != len(state.currencies):
            raise ValueError("Paper checkpoint contains duplicate currencies")
        submissions = {
            record.submission.ticket.intent.intent_id: record.submission for record in state.orders
        }
        if any(position.intent_id not in submissions for position in state.positions):
            raise ValueError("Paper checkpoint position has no submission")
        broker_events = tuple(
            event for event in state.events if event.event_id.startswith("PAPER-EVENT-")
        )
        service._broker.restore_checkpoint(
            positions=state.positions,
            quotes=tuple(quote_map.values()),
            intents=tuple(record.submission.ticket.intent for record in state.orders),
            assumptions=tuple(assumption_map.items()),
            results=tuple(record.outcome.execution_result for record in state.orders),
            events=broker_events,
        )
        for position in state.positions:
            if position.status is not PaperPositionStatus.OPEN:
                continue
            submission = submissions[position.intent_id]
            decision = service._risk_engine.evaluate_and_reserve(
                submission.risk_request,
                submission.risk_snapshot,
                submission.risk_settings,
            )
            if not decision.approved:
                reasons = ",".join(reason.value for reason in decision.reasons)
                raise ValueError(f"Paper checkpoint open exposure failed risk recovery: {reasons}")
        service._submissions = submissions
        service._orders = {
            record.submission.ticket.intent.intent_id: record for record in state.orders
        }
        service._journal = list(state.events)
        service._latest_quotes = quote_map
        service._assumptions = assumption_map
        service._currencies = currency_map
        service._event_sequence = _max_event_sequence(
            state.events,
            "PAPER-SESSION-EVENT-",
        )
        return service

    def record_restore(self, snapshot_id: str) -> None:
        with self._lock:
            self._append_session_event(
                self._now_provider(),
                "PAPER_SESSION_RESTORED",
                snapshot_id,
                "paper-session",
                {"snapshot_id": snapshot_id, "simulation_only": True},
            )

    def _position_by_id(self, position_id: str) -> PaperPosition | None:
        return next(
            (
                position
                for position in self._broker.positions(LOCAL_PAPER_ACCOUNT)
                if position.position_id == position_id
            ),
            None,
        )

    def _append_action_rejection(
        self,
        event_type: str,
        position_id: str,
        position: PaperPosition | None,
        payload: dict[str, object],
    ) -> None:
        self._append_session_event(
            self._now_provider(),
            event_type,
            position.intent_id if position is not None else position_id,
            position.product_id if position is not None else "",
            payload,
        )

    def _position_snapshot(self, position: PaperPosition) -> PaperPositionSnapshot:
        if position.status is PaperPositionStatus.CLOSED:
            return PaperPositionSnapshot(position, position.close_price, position.realized_pnl)
        quote = self._latest_quotes.get(position.product_id)
        assumptions = self._assumptions.get(position.intent_id)
        if not self._quote_is_current(quote) or assumptions is None:
            return PaperPositionSnapshot(position, None, None)
        assert quote is not None
        mark = quote.bid - assumptions.slippage_points_per_side
        if position.direction.value == "SELL":
            mark = quote.ask + assumptions.slippage_points_per_side
        price_pnl = (mark - position.entry_price) * position.quantity
        if position.direction.value == "SELL":
            price_pnl = -price_pnl
        closing_fee = assumptions.fee_per_unit_per_side * position.quantity
        return PaperPositionSnapshot(
            position=position,
            mark_price=mark,
            net_pnl=price_pnl - position.opening_fee - closing_fee,
        )

    def _quote_is_current(self, quote: PaperQuote | None) -> bool:
        if quote is None or not quote.fresh:
            return False
        age = (self._now_provider() - quote.observed_at_utc).total_seconds()
        return 0 <= age <= QUOTE_FRESHNESS_SECONDS

    def _append_new_broker_events(self, previous_count: int) -> None:
        self._journal.extend(self._broker.events()[previous_count:])

    def _append_session_event(
        self,
        timestamp_utc: datetime,
        event_type: str,
        correlation_id: str,
        instrument_id: str,
        payload: dict[str, object],
    ) -> None:
        if timestamp_utc.tzinfo is None or timestamp_utc.utcoffset() != UTC.utcoffset(
            timestamp_utc
        ):
            raise ValueError("Paper session events require UTC timestamps")
        self._event_sequence += 1
        self._journal.append(
            JournalEvent(
                event_id=f"PAPER-SESSION-EVENT-{self._event_sequence}",
                timestamp_utc=timestamp_utc,
                event_type=event_type,
                correlation_id=correlation_id,
                account_ref="paper:local-session",
                instrument_id=instrument_id,
                payload=payload,
                pnl_status=PnlStatus.UNKNOWN,
            )
        )


def _max_event_sequence(events: tuple[JournalEvent, ...], prefix: str) -> int:
    sequence = 0
    for event in events:
        if not event.event_id.startswith(prefix):
            continue
        suffix = event.event_id.removeprefix(prefix)
        if suffix.isdigit():
            sequence = max(sequence, int(suffix))
    return sequence
