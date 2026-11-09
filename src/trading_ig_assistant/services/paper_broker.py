"""Deterministic, in-memory broker that cannot route to IG."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from threading import Lock

from trading_ig_assistant.domain.adapter_contracts import (
    AccountIsolationError,
    AccountRef,
    BrokerCapabilities,
    CapabilitySupport,
    ExecutionResult,
    ExecutionStatus,
    OrderDirection,
    OrderIntent,
    ensure_account_scope,
)
from trading_ig_assistant.domain.journal import JournalEvent, PnlStatus
from trading_ig_assistant.domain.positions import (
    PaperExitReason,
    PaperFillAssumptions,
    PaperPosition,
    PaperPositionStatus,
    PaperQuote,
)
from trading_ig_assistant.domain.risk import RiskDecision


class PaperBroker:
    """Paper-only execution boundary using explicit quotes and approved intents."""

    broker_id = "paper"

    def __init__(
        self,
        accounts: tuple[AccountRef, ...],
        assumptions: PaperFillAssumptions | None = None,
    ) -> None:
        if not accounts:
            raise ValueError("PaperBroker requires at least one paper account")
        if any(
            account.broker_id != "paper" or account.environment != "paper" for account in accounts
        ):
            raise ValueError("PaperBroker accepts only paper broker/environment accounts")
        if len(set(accounts)) != len(accounts):
            raise ValueError("PaperBroker accounts must be unique")
        self._accounts = accounts
        self._assumptions = assumptions or PaperFillAssumptions()
        self._quotes: dict[str, PaperQuote] = {}
        self._approved: dict[str, OrderIntent] = {}
        self._approved_assumptions: dict[str, PaperFillAssumptions] = {}
        self._results: dict[str, ExecutionResult] = {}
        self._positions: dict[str, PaperPosition] = {}
        self._events: list[JournalEvent] = []
        self._event_sequence = 0
        self._lock = Lock()

    def capabilities(self, account: AccountRef, product_id: str) -> BrokerCapabilities:
        self._require_account(account)
        return BrokerCapabilities(
            read_accounts=CapabilitySupport.SUPPORTED,
            read_positions=CapabilitySupport.SUPPORTED,
            place_orders=CapabilitySupport.SUPPORTED,
            modify_stops=CapabilitySupport.SUPPORTED,
            close_positions=CapabilitySupport.SUPPORTED,
            native_pending_orders=CapabilitySupport.UNSUPPORTED,
            barrier_knockouts=CapabilitySupport.SUPPORTED,
            demo_execution=CapabilitySupport.UNSUPPORTED,
            live_execution=CapabilitySupport.UNSUPPORTED,
        )

    def accounts(self) -> tuple[AccountRef, ...]:
        return self._accounts

    def positions(self, account: AccountRef) -> tuple[PaperPosition, ...]:
        self._require_account(account)
        with self._lock:
            return tuple(
                position for position in self._positions.values() if position.account == account
            )

    def events(self) -> tuple[JournalEvent, ...]:
        with self._lock:
            return tuple(self._events)

    def publish_quote(self, quote: PaperQuote) -> None:
        with self._lock:
            previous = self._quotes.get(quote.product_id)
            if previous is not None and quote.observed_at_utc < previous.observed_at_utc:
                raise ValueError("paper quotes cannot move backward in time")
            self._quotes[quote.product_id] = quote

    def restore_checkpoint(
        self,
        *,
        positions: tuple[PaperPosition, ...],
        quotes: tuple[PaperQuote, ...],
        intents: tuple[OrderIntent, ...],
        assumptions: tuple[tuple[str, PaperFillAssumptions], ...],
        results: tuple[ExecutionResult, ...],
        events: tuple[JournalEvent, ...],
    ) -> None:
        """Restore one validated local checkpoint into an otherwise empty Paper broker."""

        with self._lock:
            if any(
                (
                    self._quotes,
                    self._approved,
                    self._results,
                    self._positions,
                    self._events,
                )
            ):
                raise ValueError("Paper broker restore requires an empty broker")
            if any(position.account not in self._accounts for position in positions):
                raise AccountIsolationError("Paper checkpoint contains an unknown account")
            position_ids = [position.position_id for position in positions]
            intent_ids = [intent.intent_id for intent in intents]
            quote_ids = [quote.product_id for quote in quotes]
            if len(set(position_ids)) != len(position_ids):
                raise ValueError("Paper checkpoint contains duplicate position IDs")
            if len(set(intent_ids)) != len(intent_ids):
                raise ValueError("Paper checkpoint contains duplicate intent IDs")
            if len(set(quote_ids)) != len(quote_ids):
                raise ValueError("Paper checkpoint contains duplicate product quotes")
            assumption_map = dict(assumptions)
            if len(assumption_map) != len(assumptions):
                raise ValueError("Paper checkpoint contains duplicate fill assumptions")
            result_map = {result.intent_id: result for result in results}
            if len(result_map) != len(results):
                raise ValueError("Paper checkpoint contains duplicate execution results")
            intent_map = {intent.intent_id: intent for intent in intents}
            if any(result.account not in self._accounts for result in results):
                raise AccountIsolationError("Paper checkpoint result has an unknown account")
            if any(position.intent_id not in intent_map for position in positions):
                raise ValueError("Paper checkpoint position has no matching intent")
            if any(position.intent_id not in assumption_map for position in positions):
                raise ValueError("Paper checkpoint position has no fill assumptions")

            self._quotes = {quote.product_id: quote for quote in quotes}
            self._approved = intent_map
            self._approved_assumptions = assumption_map
            self._results = result_map
            self._positions = {position.position_id: position for position in positions}
            self._events = list(events)
            self._event_sequence = _max_event_sequence(events, "PAPER-EVENT-")

    def authorize(
        self,
        intent: OrderIntent,
        decision: RiskDecision,
        assumptions: PaperFillAssumptions | None = None,
    ) -> None:
        """Record one approved risk decision before standard broker submission."""
        self._require_account(intent.account)
        if not decision.approved:
            raise ValueError("rejected risk decision cannot authorize paper execution")
        approved_assumptions = assumptions or self._assumptions
        with self._lock:
            existing = self._approved.get(intent.intent_id)
            if existing is not None and existing != intent:
                raise ValueError("intent_id already authorized with different content")
            existing_assumptions = self._approved_assumptions.get(intent.intent_id)
            if existing_assumptions is not None and existing_assumptions != approved_assumptions:
                raise ValueError("intent_id already authorized with different fill assumptions")
            self._approved[intent.intent_id] = intent
            self._approved_assumptions[intent.intent_id] = approved_assumptions

    def submit(self, intent: OrderIntent) -> ExecutionResult:
        self._require_account(intent.account)
        with self._lock:
            cached = self._results.get(intent.intent_id)
            if cached is not None:
                return cached
            if self._approved.get(intent.intent_id) != intent:
                return self._reject(intent, "RISK_APPROVAL_REQUIRED")
            assumptions = self._approved_assumptions[intent.intent_id]
            quote = self._quotes.get(intent.product_id)
            if quote is None:
                return self._reject(intent, "PAPER_QUOTE_MISSING")
            if quote.observed_at_utc >= intent.expires_at_utc:
                return self._reject(intent, "INTENT_EXPIRED")
            if not quote.fresh:
                return self._reject(intent, "STALE_PRICE")
            if not quote.market_open:
                return self._reject(intent, "MARKET_CLOSED")
            if not quote.product_supported:
                return self._reject(intent, "PRODUCT_UNSUPPORTED")

            slippage = assumptions.slippage_points_per_side
            entry_price = quote.ask + slippage
            if intent.direction is OrderDirection.SELL:
                entry_price = quote.bid - slippage
            if entry_price <= 0:
                return self._reject(intent, "INVALID_SIMULATED_FILL")
            if not self._levels_valid(intent, entry_price):
                return self._reject(intent, "INVALID_DIRECTIONAL_LEVELS")
            position_id = f"PAPER-{intent.intent_id}"
            opening_fee = assumptions.fee_per_unit_per_side * intent.quantity
            position = PaperPosition(
                position_id=position_id,
                intent_id=intent.intent_id,
                account=intent.account,
                product_id=intent.product_id,
                underlying_id=intent.underlying_id,
                direction=intent.direction,
                quantity=intent.quantity,
                entry_price=entry_price,
                current_stop=intent.requested_stop,
                target=intent.requested_target,
                knockout=intent.requested_ko,
                opened_at_utc=quote.observed_at_utc,
                opening_fee=opening_fee,
                entry_slippage=slippage,
                currency=quote.currency,
                price_provenance=quote.provenance,
                fill_model_version=assumptions.model_version,
            )
            self._positions[position_id] = position
            result = ExecutionResult(
                intent_id=intent.intent_id,
                account=intent.account,
                status=ExecutionStatus.CONFIRMED,
                broker_reference=position_id,
                message="PAPER_FILL_CONFIRMED",
            )
            self._results[intent.intent_id] = result
            self._record(
                position,
                quote,
                "PAPER_POSITION_OPENED",
                {
                    "entry_price": str(entry_price),
                    "quantity": str(intent.quantity),
                    "opening_fee": str(opening_fee),
                    "slippage": str(slippage),
                    "fill_model": assumptions.model_version,
                    "price_provenance": quote.provenance,
                },
            )
            return result

    def reconcile(self, account: AccountRef, intent_id: str) -> ExecutionResult:
        self._require_account(account)
        with self._lock:
            result = self._results.get(intent_id)
            if result is not None:
                ensure_account_scope(account, result.account)
                return result
            return ExecutionResult(
                intent_id=intent_id,
                account=account,
                status=ExecutionStatus.UNKNOWN,
                message="PAPER_INTENT_NOT_FOUND",
            )

    def move_stop(
        self,
        account: AccountRef,
        position_id: str,
        stop: Decimal,
    ) -> ExecutionResult:
        self._require_account(account)
        if stop <= 0:
            return self._position_rejection(account, position_id, "INVALID_STOP")
        with self._lock:
            position = self._open_position(account, position_id)
            if position is None:
                return self._position_rejection(account, position_id, "OPEN_POSITION_NOT_FOUND")
            current = position.current_stop
            widening = current is not None and (
                (position.direction is OrderDirection.BUY and stop < current)
                or (position.direction is OrderDirection.SELL and stop > current)
            )
            if widening:
                return self._position_rejection(account, position_id, "STOP_WIDENING_FORBIDDEN")
            quote = self._quotes.get(position.product_id)
            if quote is None:
                return self._position_rejection(account, position_id, "PAPER_QUOTE_MISSING")
            self._positions[position_id] = replace(position, current_stop=stop)
            result = ExecutionResult(
                intent_id=position.intent_id,
                account=account,
                status=ExecutionStatus.CONFIRMED,
                broker_reference=position_id,
                message="PAPER_STOP_CONFIRMED",
            )
            self._record(
                self._positions[position_id],
                quote,
                "PAPER_STOP_CONFIRMED",
                {"old_stop": str(current), "new_stop": str(stop)},
            )
            return result

    def close(self, account: AccountRef, position_id: str) -> ExecutionResult:
        self._require_account(account)
        with self._lock:
            position = self._open_position(account, position_id)
            if position is None:
                return self._position_rejection(account, position_id, "OPEN_POSITION_NOT_FOUND")
            quote = self._quotes.get(position.product_id)
            if quote is None:
                return self._position_rejection(account, position_id, "PAPER_QUOTE_MISSING")
            if not quote.fresh:
                return self._position_rejection(account, position_id, "STALE_PRICE")
            return self._close_locked(position, quote, PaperExitReason.MANUAL)

    def process_quote(self, quote: PaperQuote) -> tuple[ExecutionResult, ...]:
        """Apply one chronological quote and close paper stops/targets/KO at executable side."""
        with self._lock:
            previous = self._quotes.get(quote.product_id)
            if previous is not None and quote.observed_at_utc < previous.observed_at_utc:
                raise ValueError("paper quotes cannot move backward in time")
            self._quotes[quote.product_id] = quote
            if not quote.fresh or not quote.market_open or not quote.product_supported:
                return ()
            results: list[ExecutionResult] = []
            for position in tuple(self._positions.values()):
                if (
                    position.product_id != quote.product_id
                    or position.status is not PaperPositionStatus.OPEN
                ):
                    continue
                exit_reason = self._exit_reason(position, quote)
                if exit_reason is not None:
                    results.append(self._close_locked(position, quote, exit_reason))
            return tuple(results)

    def _exit_reason(self, position: PaperPosition, quote: PaperQuote) -> PaperExitReason | None:
        executable = quote.bid if position.direction is OrderDirection.BUY else quote.ask
        if position.direction is OrderDirection.BUY:
            if position.knockout is not None and executable <= position.knockout:
                return PaperExitReason.KNOCKOUT
            if position.current_stop is not None and executable <= position.current_stop:
                return PaperExitReason.STOP
            if position.target is not None and executable >= position.target:
                return PaperExitReason.TARGET
        else:
            if position.knockout is not None and executable >= position.knockout:
                return PaperExitReason.KNOCKOUT
            if position.current_stop is not None and executable >= position.current_stop:
                return PaperExitReason.STOP
            if position.target is not None and executable <= position.target:
                return PaperExitReason.TARGET
        return None

    @staticmethod
    def _levels_valid(intent: OrderIntent, entry_price: Decimal) -> bool:
        if intent.direction is OrderDirection.BUY:
            return (
                (intent.requested_stop is None or intent.requested_stop < entry_price)
                and (intent.requested_target is None or intent.requested_target > entry_price)
                and (intent.requested_ko is None or intent.requested_ko < entry_price)
            )
        return (
            (intent.requested_stop is None or intent.requested_stop > entry_price)
            and (intent.requested_target is None or intent.requested_target < entry_price)
            and (intent.requested_ko is None or intent.requested_ko > entry_price)
        )

    def _close_locked(
        self,
        position: PaperPosition,
        quote: PaperQuote,
        reason: PaperExitReason,
    ) -> ExecutionResult:
        assumptions = self._approved_assumptions.get(position.intent_id, self._assumptions)
        slippage = assumptions.slippage_points_per_side
        close_price = quote.bid - slippage
        if position.direction is OrderDirection.SELL:
            close_price = quote.ask + slippage
        if close_price <= 0:
            return self._position_rejection(
                position.account,
                position.position_id,
                "INVALID_SIMULATED_FILL",
            )
        closing_fee = assumptions.fee_per_unit_per_side * position.quantity
        price_pnl = (close_price - position.entry_price) * position.quantity
        if position.direction is OrderDirection.SELL:
            price_pnl = -price_pnl
        realized_pnl = price_pnl - position.opening_fee - closing_fee
        closed = replace(
            position,
            status=PaperPositionStatus.CLOSED,
            closed_at_utc=quote.observed_at_utc,
            close_price=close_price,
            closing_fee=closing_fee,
            realized_pnl=realized_pnl,
            exit_reason=reason,
        )
        self._positions[position.position_id] = closed
        result = ExecutionResult(
            intent_id=position.intent_id,
            account=position.account,
            status=ExecutionStatus.CONFIRMED,
            broker_reference=position.position_id,
            message=f"PAPER_POSITION_CLOSED:{reason.value}",
        )
        self._record(
            closed,
            quote,
            "PAPER_POSITION_CLOSED",
            {
                "close_price": str(close_price),
                "closing_fee": str(closing_fee),
                "exit_reason": reason.value,
                "fill_model": assumptions.model_version,
                "price_provenance": quote.provenance,
            },
            pnl_amount=realized_pnl,
        )
        return result

    def _reject(self, intent: OrderIntent, reason: str) -> ExecutionResult:
        result = ExecutionResult(
            intent_id=intent.intent_id,
            account=intent.account,
            status=ExecutionStatus.REJECTED,
            message=reason,
        )
        self._results[intent.intent_id] = result
        return result

    @staticmethod
    def _position_rejection(
        account: AccountRef,
        position_id: str,
        reason: str,
    ) -> ExecutionResult:
        return ExecutionResult(
            intent_id=position_id,
            account=account,
            status=ExecutionStatus.REJECTED,
            broker_reference=position_id,
            message=reason,
        )

    def _open_position(self, account: AccountRef, position_id: str) -> PaperPosition | None:
        position = self._positions.get(position_id)
        if position is None:
            return None
        ensure_account_scope(account, position.account)
        if position.status is not PaperPositionStatus.OPEN:
            return None
        return position

    def _require_account(self, account: AccountRef) -> None:
        if account.broker_id != "paper" or account.environment != "paper":
            raise AccountIsolationError("PaperBroker rejects non-paper account scope")
        if account not in self._accounts:
            raise AccountIsolationError("PaperBroker account is not registered")

    def _record(
        self,
        position: PaperPosition,
        quote: PaperQuote,
        event_type: str,
        payload: dict[str, str],
        *,
        pnl_amount: Decimal | None = None,
    ) -> None:
        self._event_sequence += 1
        self._events.append(
            JournalEvent(
                event_id=f"PAPER-EVENT-{self._event_sequence}",
                timestamp_utc=quote.observed_at_utc,
                event_type=event_type,
                correlation_id=position.intent_id,
                account_ref=f"paper:{position.account.account_id}",
                instrument_id=position.product_id,
                payload=payload,
                pnl_amount=pnl_amount,
                pnl_currency=position.currency if pnl_amount is not None else None,
                pnl_status=PnlStatus.REALIZED if pnl_amount is not None else PnlStatus.UNKNOWN,
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
