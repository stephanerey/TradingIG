"""Strict JSON codec for local Paper-session checkpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from trading_ig_assistant.domain.adapter_contracts import (
    AccountRef,
    ExecutionResult,
    ExecutionStatus,
    OrderDirection,
    OrderIntent,
)
from trading_ig_assistant.domain.journal import JournalEvent, PnlStatus
from trading_ig_assistant.domain.positions import (
    PaperExitReason,
    PaperFillAssumptions,
    PaperPosition,
    PaperPositionStatus,
    PaperQuote,
)
from trading_ig_assistant.domain.risk import (
    AccountRiskState,
    ExposureState,
    PortfolioRiskSnapshot,
    ResolvedRiskSettings,
    RiskAction,
    RiskDecision,
    RiskDecisionStatus,
    RiskLimits,
    RiskRejectionReason,
    RiskRequest,
)
from trading_ig_assistant.domain.tickets import TicketDraft
from trading_ig_assistant.services.order_execution_coordinator import PaperExecutionOutcome
from trading_ig_assistant.services.paper_session import (
    PaperOrderRecord,
    PaperSessionState,
    PaperTicketSubmission,
)

PAPER_CHECKPOINT_FORMAT_VERSION = 1


def encode_paper_session_state(state: PaperSessionState) -> dict[str, Any]:
    return {
        "format_version": PAPER_CHECKPOINT_FORMAT_VERSION,
        "session_id": state.session_id,
        "orders": [_encode_order(record) for record in state.orders],
        "positions": [_encode_position(position) for position in state.positions],
        "events": [_encode_event(event) for event in state.events],
        "latest_quotes": [
            {"product_id": product_id, "quote": _encode_quote(quote)}
            for product_id, quote in state.latest_quotes
        ],
        "assumptions": [
            {"intent_id": intent_id, "value": _encode_assumptions(value)}
            for intent_id, value in state.assumptions
        ],
        "currencies": [
            {"product_id": product_id, "currency": currency}
            for product_id, currency in state.currencies
        ],
    }


def decode_paper_session_state(payload: dict[str, Any]) -> PaperSessionState:
    root = _object(payload, "checkpoint")
    if _integer(root.get("format_version"), "format_version") != PAPER_CHECKPOINT_FORMAT_VERSION:
        raise ValueError("Unsupported Paper checkpoint format version")
    return PaperSessionState(
        session_id=_text(root.get("session_id"), "session_id"),
        orders=tuple(_decode_order(_object(item, "order")) for item in _items(root, "orders")),
        positions=tuple(
            _decode_position(_object(item, "position")) for item in _items(root, "positions")
        ),
        events=tuple(_decode_event(_object(item, "event")) for item in _items(root, "events")),
        latest_quotes=tuple(
            (
                _text(entry.get("product_id"), "latest_quote.product_id"),
                _decode_quote(_object(entry.get("quote"), "latest_quote.quote")),
            )
            for entry in (_object(item, "latest_quote") for item in _items(root, "latest_quotes"))
        ),
        assumptions=tuple(
            (
                _text(entry.get("intent_id"), "assumption.intent_id"),
                _decode_assumptions(_object(entry.get("value"), "assumption.value")),
            )
            for entry in (_object(item, "assumption") for item in _items(root, "assumptions"))
        ),
        currencies=tuple(
            (
                _text(entry.get("product_id"), "currency.product_id"),
                _text(entry.get("currency"), "currency.value"),
            )
            for entry in (_object(item, "currency") for item in _items(root, "currencies"))
        ),
    )


def _encode_order(record: PaperOrderRecord) -> dict[str, Any]:
    return {
        "submission": _encode_submission(record.submission),
        "outcome": {
            "risk_decision": _encode_risk_decision(record.outcome.risk_decision),
            "execution_result": _encode_execution_result(record.outcome.execution_result),
        },
        "submitted_at_utc": _datetime_text(record.submitted_at_utc),
    }


def _decode_order(value: dict[str, Any]) -> PaperOrderRecord:
    outcome = _object(value.get("outcome"), "order.outcome")
    return PaperOrderRecord(
        submission=_decode_submission(_object(value.get("submission"), "order.submission")),
        outcome=PaperExecutionOutcome(
            risk_decision=_decode_risk_decision(
                _object(outcome.get("risk_decision"), "outcome.risk_decision")
            ),
            execution_result=_decode_execution_result(
                _object(outcome.get("execution_result"), "outcome.execution_result")
            ),
        ),
        submitted_at_utc=_datetime_value(
            value.get("submitted_at_utc"),
            "order.submitted_at_utc",
        ),
    )


def _encode_submission(value: PaperTicketSubmission) -> dict[str, Any]:
    return {
        "ticket": _encode_ticket(value.ticket),
        "risk_request": _encode_risk_request(value.risk_request),
        "risk_snapshot": _encode_risk_snapshot(value.risk_snapshot),
        "risk_settings": _encode_risk_settings(value.risk_settings),
        "quote": _encode_quote(value.quote),
        "assumptions": _encode_assumptions(value.assumptions),
    }


def _decode_submission(value: dict[str, Any]) -> PaperTicketSubmission:
    return PaperTicketSubmission(
        ticket=_decode_ticket(_object(value.get("ticket"), "submission.ticket")),
        risk_request=_decode_risk_request(
            _object(value.get("risk_request"), "submission.risk_request")
        ),
        risk_snapshot=_decode_risk_snapshot(
            _object(value.get("risk_snapshot"), "submission.risk_snapshot")
        ),
        risk_settings=_decode_risk_settings(
            _object(value.get("risk_settings"), "submission.risk_settings")
        ),
        quote=_decode_quote(_object(value.get("quote"), "submission.quote")),
        assumptions=_decode_assumptions(
            _object(value.get("assumptions"), "submission.assumptions")
        ),
    )


def _encode_ticket(value: TicketDraft) -> dict[str, Any]:
    return {
        "intent": _encode_intent(value.intent),
        "entry_price": str(value.entry_price),
        "spread_cost": str(value.spread_cost),
        "fee_estimate": str(value.fee_estimate),
        "slippage_estimate": str(value.slippage_estimate),
        "estimated_loss": str(value.estimated_loss),
        "estimated_gain": _optional_decimal_text(value.estimated_gain),
        "reward_risk_ratio": _optional_decimal_text(value.reward_risk_ratio),
        "scanner_ranking": _optional_decimal_text(value.scanner_ranking),
        "scanner_commentary": value.scanner_commentary,
        "warnings": list(value.warnings),
    }


def _decode_ticket(value: dict[str, Any]) -> TicketDraft:
    return TicketDraft(
        intent=_decode_intent(_object(value.get("intent"), "ticket.intent")),
        entry_price=_decimal_value(value.get("entry_price"), "ticket.entry_price"),
        spread_cost=_decimal_value(value.get("spread_cost"), "ticket.spread_cost"),
        fee_estimate=_decimal_value(value.get("fee_estimate"), "ticket.fee_estimate"),
        slippage_estimate=_decimal_value(
            value.get("slippage_estimate"),
            "ticket.slippage_estimate",
        ),
        estimated_loss=_decimal_value(value.get("estimated_loss"), "ticket.estimated_loss"),
        estimated_gain=_optional_decimal_value(
            value.get("estimated_gain"),
            "ticket.estimated_gain",
        ),
        reward_risk_ratio=_optional_decimal_value(
            value.get("reward_risk_ratio"),
            "ticket.reward_risk_ratio",
        ),
        scanner_ranking=_optional_decimal_value(
            value.get("scanner_ranking"),
            "ticket.scanner_ranking",
        ),
        scanner_commentary=_text_allow_empty(
            value.get("scanner_commentary"),
            "ticket.scanner_commentary",
        ),
        warnings=tuple(_text(item, "ticket.warning") for item in _list(value.get("warnings"))),
    )


def _encode_intent(value: OrderIntent) -> dict[str, Any]:
    return {
        "intent_id": value.intent_id,
        "account": _encode_account(value.account),
        "product_id": value.product_id,
        "underlying_id": value.underlying_id,
        "direction": value.direction.value,
        "quantity": str(value.quantity),
        "requested_stop": _optional_decimal_text(value.requested_stop),
        "requested_target": _optional_decimal_text(value.requested_target),
        "requested_ko": _optional_decimal_text(value.requested_ko),
        "signal_id": value.signal_id,
        "expires_at_utc": _datetime_text(value.expires_at_utc),
    }


def _decode_intent(value: dict[str, Any]) -> OrderIntent:
    return OrderIntent(
        intent_id=_text(value.get("intent_id"), "intent.intent_id"),
        account=_decode_account(_object(value.get("account"), "intent.account")),
        product_id=_text(value.get("product_id"), "intent.product_id"),
        underlying_id=_text(value.get("underlying_id"), "intent.underlying_id"),
        direction=OrderDirection(_text(value.get("direction"), "intent.direction")),
        quantity=_decimal_value(value.get("quantity"), "intent.quantity"),
        requested_stop=_optional_decimal_value(
            value.get("requested_stop"),
            "intent.requested_stop",
        ),
        requested_target=_optional_decimal_value(
            value.get("requested_target"),
            "intent.requested_target",
        ),
        requested_ko=_optional_decimal_value(
            value.get("requested_ko"),
            "intent.requested_ko",
        ),
        signal_id=_optional_text(value.get("signal_id"), "intent.signal_id"),
        expires_at_utc=_datetime_value(value.get("expires_at_utc"), "intent.expires_at_utc"),
    )


def _encode_risk_request(value: RiskRequest) -> dict[str, Any]:
    return {
        "intent_id": value.intent_id,
        "account": _encode_account(value.account),
        "underlying_id": value.underlying_id,
        "action": value.action.value,
        "estimated_stop_loss": _optional_decimal_text(value.estimated_stop_loss),
        "anticipated_costs": str(value.anticipated_costs),
        "scenario_slippage": str(value.scenario_slippage),
        "maximum_ko_loss": _optional_decimal_text(value.maximum_ko_loss),
        "price_fresh": value.price_fresh,
        "market_open": value.market_open,
        "product_supported": value.product_supported,
    }


def _decode_risk_request(value: dict[str, Any]) -> RiskRequest:
    return RiskRequest(
        intent_id=_text(value.get("intent_id"), "risk_request.intent_id"),
        account=_decode_account(_object(value.get("account"), "risk_request.account")),
        underlying_id=_text(value.get("underlying_id"), "risk_request.underlying_id"),
        action=RiskAction(_text(value.get("action"), "risk_request.action")),
        estimated_stop_loss=_optional_decimal_value(
            value.get("estimated_stop_loss"),
            "risk_request.estimated_stop_loss",
        ),
        anticipated_costs=_decimal_value(
            value.get("anticipated_costs"),
            "risk_request.anticipated_costs",
        ),
        scenario_slippage=_decimal_value(
            value.get("scenario_slippage"),
            "risk_request.scenario_slippage",
        ),
        maximum_ko_loss=_optional_decimal_value(
            value.get("maximum_ko_loss"),
            "risk_request.maximum_ko_loss",
        ),
        price_fresh=_boolean(value.get("price_fresh"), "risk_request.price_fresh"),
        market_open=_boolean(value.get("market_open"), "risk_request.market_open"),
        product_supported=_boolean(
            value.get("product_supported"),
            "risk_request.product_supported",
        ),
    )


def _encode_risk_snapshot(value: PortfolioRiskSnapshot) -> dict[str, Any]:
    return {
        "reference_currency": value.reference_currency,
        "accounts": [_encode_account_risk(account) for account in value.accounts],
        "open_exposures": [_encode_exposure(item) for item in value.open_exposures],
        "exposure_complete": value.exposure_complete,
    }


def _decode_risk_snapshot(value: dict[str, Any]) -> PortfolioRiskSnapshot:
    return PortfolioRiskSnapshot(
        reference_currency=_text(
            value.get("reference_currency"),
            "risk_snapshot.reference_currency",
        ),
        accounts=tuple(
            _decode_account_risk(_object(item, "risk_snapshot.account"))
            for item in _list(value.get("accounts"))
        ),
        open_exposures=tuple(
            _decode_exposure(_object(item, "risk_snapshot.exposure"))
            for item in _list(value.get("open_exposures"))
        ),
        exposure_complete=_boolean(
            value.get("exposure_complete"),
            "risk_snapshot.exposure_complete",
        ),
    )


def _encode_account_risk(value: AccountRiskState) -> dict[str, Any]:
    return {
        "account": _encode_account(value.account),
        "currency": value.currency,
        "equity_reference_day": str(value.equity_reference_day),
        "equity_current": str(value.equity_current),
        "daily_net_pnl": str(value.daily_net_pnl),
        "confirmed": value.confirmed,
        "active_for_opening": value.active_for_opening,
        "fx_rate_to_reference": _optional_decimal_text(value.fx_rate_to_reference),
    }


def _decode_account_risk(value: dict[str, Any]) -> AccountRiskState:
    return AccountRiskState(
        account=_decode_account(_object(value.get("account"), "account_risk.account")),
        currency=_text(value.get("currency"), "account_risk.currency"),
        equity_reference_day=_decimal_value(
            value.get("equity_reference_day"),
            "account_risk.equity_reference_day",
        ),
        equity_current=_decimal_value(
            value.get("equity_current"),
            "account_risk.equity_current",
        ),
        daily_net_pnl=_decimal_value(
            value.get("daily_net_pnl"),
            "account_risk.daily_net_pnl",
        ),
        confirmed=_boolean(value.get("confirmed"), "account_risk.confirmed"),
        active_for_opening=_boolean(
            value.get("active_for_opening"),
            "account_risk.active_for_opening",
        ),
        fx_rate_to_reference=_optional_decimal_value(
            value.get("fx_rate_to_reference"),
            "account_risk.fx_rate_to_reference",
        ),
    )


def _encode_exposure(value: ExposureState) -> dict[str, Any]:
    return {
        "exposure_id": value.exposure_id,
        "account": _encode_account(value.account),
        "underlying_id": value.underlying_id,
        "origin_intent_id": value.origin_intent_id,
    }


def _decode_exposure(value: dict[str, Any]) -> ExposureState:
    return ExposureState(
        exposure_id=_text(value.get("exposure_id"), "exposure.exposure_id"),
        account=_decode_account(_object(value.get("account"), "exposure.account")),
        underlying_id=_text(value.get("underlying_id"), "exposure.underlying_id"),
        origin_intent_id=_optional_text(
            value.get("origin_intent_id"),
            "exposure.origin_intent_id",
        ),
    )


def _encode_risk_settings(value: ResolvedRiskSettings) -> dict[str, Any]:
    limits = value.limits
    return {
        "limits": {
            "per_trade_fraction": str(limits.per_trade_fraction),
            "daily_loss_fraction": str(limits.daily_loss_fraction),
            "max_open_global": limits.max_open_global,
            "max_open_per_underlying": limits.max_open_per_underlying,
        },
        "sources": [[name, source] for name, source in value.sources],
    }


def _decode_risk_settings(value: dict[str, Any]) -> ResolvedRiskSettings:
    limits = _object(value.get("limits"), "risk_settings.limits")
    sources: list[tuple[str, str]] = []
    for item in _list(value.get("sources")):
        pair = _list(item)
        if len(pair) != 2:
            raise ValueError("risk_settings source must contain name and source")
        sources.append(
            (
                _text(pair[0], "risk_settings.source.name"),
                _text(pair[1], "risk_settings.source.value"),
            )
        )
    return ResolvedRiskSettings(
        limits=RiskLimits(
            per_trade_fraction=_decimal_value(
                limits.get("per_trade_fraction"),
                "risk_limits.per_trade_fraction",
            ),
            daily_loss_fraction=_decimal_value(
                limits.get("daily_loss_fraction"),
                "risk_limits.daily_loss_fraction",
            ),
            max_open_global=_integer(
                limits.get("max_open_global"),
                "risk_limits.max_open_global",
            ),
            max_open_per_underlying=_integer(
                limits.get("max_open_per_underlying"),
                "risk_limits.max_open_per_underlying",
            ),
        ),
        sources=tuple(sources),
    )


def _encode_risk_decision(value: RiskDecision) -> dict[str, Any]:
    return {
        "status": value.status.value,
        "reasons": [reason.value for reason in value.reasons],
        "budget_reference": _optional_decimal_text(value.budget_reference),
        "estimated_loss_reference": _optional_decimal_text(value.estimated_loss_reference),
    }


def _decode_risk_decision(value: dict[str, Any]) -> RiskDecision:
    return RiskDecision(
        status=RiskDecisionStatus(_text(value.get("status"), "risk_decision.status")),
        reasons=tuple(
            RiskRejectionReason(_text(item, "risk_decision.reason"))
            for item in _list(value.get("reasons"))
        ),
        budget_reference=_optional_decimal_value(
            value.get("budget_reference"),
            "risk_decision.budget_reference",
        ),
        estimated_loss_reference=_optional_decimal_value(
            value.get("estimated_loss_reference"),
            "risk_decision.estimated_loss_reference",
        ),
    )


def _encode_execution_result(value: ExecutionResult) -> dict[str, Any]:
    return {
        "intent_id": value.intent_id,
        "account": _encode_account(value.account),
        "status": value.status.value,
        "broker_reference": value.broker_reference,
        "message": value.message,
    }


def _decode_execution_result(value: dict[str, Any]) -> ExecutionResult:
    return ExecutionResult(
        intent_id=_text(value.get("intent_id"), "execution_result.intent_id"),
        account=_decode_account(_object(value.get("account"), "execution_result.account")),
        status=ExecutionStatus(_text(value.get("status"), "execution_result.status")),
        broker_reference=_optional_text(
            value.get("broker_reference"),
            "execution_result.broker_reference",
        ),
        message=_optional_text(value.get("message"), "execution_result.message"),
    )


def _encode_position(value: PaperPosition) -> dict[str, Any]:
    return {
        "position_id": value.position_id,
        "intent_id": value.intent_id,
        "account": _encode_account(value.account),
        "product_id": value.product_id,
        "underlying_id": value.underlying_id,
        "direction": value.direction.value,
        "quantity": str(value.quantity),
        "entry_price": str(value.entry_price),
        "current_stop": _optional_decimal_text(value.current_stop),
        "target": _optional_decimal_text(value.target),
        "knockout": _optional_decimal_text(value.knockout),
        "opened_at_utc": _datetime_text(value.opened_at_utc),
        "opening_fee": str(value.opening_fee),
        "entry_slippage": str(value.entry_slippage),
        "currency": value.currency,
        "price_provenance": value.price_provenance,
        "fill_model_version": value.fill_model_version,
        "status": value.status.value,
        "closed_at_utc": _optional_datetime_text(value.closed_at_utc),
        "close_price": _optional_decimal_text(value.close_price),
        "closing_fee": _optional_decimal_text(value.closing_fee),
        "realized_pnl": _optional_decimal_text(value.realized_pnl),
        "exit_reason": value.exit_reason.value if value.exit_reason is not None else None,
    }


def _decode_position(value: dict[str, Any]) -> PaperPosition:
    exit_reason = _optional_text(value.get("exit_reason"), "position.exit_reason")
    return PaperPosition(
        position_id=_text(value.get("position_id"), "position.position_id"),
        intent_id=_text(value.get("intent_id"), "position.intent_id"),
        account=_decode_account(_object(value.get("account"), "position.account")),
        product_id=_text(value.get("product_id"), "position.product_id"),
        underlying_id=_text(value.get("underlying_id"), "position.underlying_id"),
        direction=OrderDirection(_text(value.get("direction"), "position.direction")),
        quantity=_decimal_value(value.get("quantity"), "position.quantity"),
        entry_price=_decimal_value(value.get("entry_price"), "position.entry_price"),
        current_stop=_optional_decimal_value(value.get("current_stop"), "position.current_stop"),
        target=_optional_decimal_value(value.get("target"), "position.target"),
        knockout=_optional_decimal_value(value.get("knockout"), "position.knockout"),
        opened_at_utc=_datetime_value(value.get("opened_at_utc"), "position.opened_at_utc"),
        opening_fee=_decimal_value(value.get("opening_fee"), "position.opening_fee"),
        entry_slippage=_decimal_value(
            value.get("entry_slippage"),
            "position.entry_slippage",
        ),
        currency=_text(value.get("currency"), "position.currency"),
        price_provenance=_text(
            value.get("price_provenance"),
            "position.price_provenance",
        ),
        fill_model_version=_text(
            value.get("fill_model_version"),
            "position.fill_model_version",
        ),
        status=PaperPositionStatus(_text(value.get("status"), "position.status")),
        closed_at_utc=_optional_datetime_value(
            value.get("closed_at_utc"),
            "position.closed_at_utc",
        ),
        close_price=_optional_decimal_value(value.get("close_price"), "position.close_price"),
        closing_fee=_optional_decimal_value(value.get("closing_fee"), "position.closing_fee"),
        realized_pnl=_optional_decimal_value(value.get("realized_pnl"), "position.realized_pnl"),
        exit_reason=PaperExitReason(exit_reason) if exit_reason is not None else None,
    )


def _encode_quote(value: PaperQuote) -> dict[str, Any]:
    return {
        "product_id": value.product_id,
        "observed_at_utc": _datetime_text(value.observed_at_utc),
        "bid": str(value.bid),
        "ask": str(value.ask),
        "currency": value.currency,
        "fresh": value.fresh,
        "market_open": value.market_open,
        "product_supported": value.product_supported,
        "provenance": value.provenance,
    }


def _decode_quote(value: dict[str, Any]) -> PaperQuote:
    return PaperQuote(
        product_id=_text(value.get("product_id"), "quote.product_id"),
        observed_at_utc=_datetime_value(value.get("observed_at_utc"), "quote.observed_at_utc"),
        bid=_decimal_value(value.get("bid"), "quote.bid"),
        ask=_decimal_value(value.get("ask"), "quote.ask"),
        currency=_text(value.get("currency"), "quote.currency"),
        fresh=_boolean(value.get("fresh"), "quote.fresh"),
        market_open=_boolean(value.get("market_open"), "quote.market_open"),
        product_supported=_boolean(
            value.get("product_supported"),
            "quote.product_supported",
        ),
        provenance=_text(value.get("provenance"), "quote.provenance"),
    )


def _encode_assumptions(value: PaperFillAssumptions) -> dict[str, Any]:
    return {
        "fee_per_unit_per_side": str(value.fee_per_unit_per_side),
        "slippage_points_per_side": str(value.slippage_points_per_side),
        "model_version": value.model_version,
    }


def _decode_assumptions(value: dict[str, Any]) -> PaperFillAssumptions:
    return PaperFillAssumptions(
        fee_per_unit_per_side=_decimal_value(
            value.get("fee_per_unit_per_side"),
            "assumptions.fee_per_unit_per_side",
        ),
        slippage_points_per_side=_decimal_value(
            value.get("slippage_points_per_side"),
            "assumptions.slippage_points_per_side",
        ),
        model_version=_text(value.get("model_version"), "assumptions.model_version"),
    )


def _encode_event(value: JournalEvent) -> dict[str, Any]:
    return {
        "event_id": value.event_id,
        "timestamp_utc": _datetime_text(value.timestamp_utc),
        "event_type": value.event_type,
        "correlation_id": value.correlation_id,
        "account_ref": value.account_ref,
        "instrument_id": value.instrument_id,
        "payload": value.payload,
        "pnl_amount": _optional_decimal_text(value.pnl_amount),
        "pnl_currency": value.pnl_currency,
        "pnl_status": value.pnl_status.value,
    }


def _decode_event(value: dict[str, Any]) -> JournalEvent:
    payload = _object(value.get("payload"), "event.payload")
    return JournalEvent(
        event_id=_text(value.get("event_id"), "event.event_id"),
        timestamp_utc=_datetime_value(value.get("timestamp_utc"), "event.timestamp_utc"),
        event_type=_text(value.get("event_type"), "event.event_type"),
        correlation_id=_text(value.get("correlation_id"), "event.correlation_id"),
        account_ref=_text(value.get("account_ref"), "event.account_ref"),
        instrument_id=_optional_text(value.get("instrument_id"), "event.instrument_id"),
        payload=payload,
        pnl_amount=_optional_decimal_value(value.get("pnl_amount"), "event.pnl_amount"),
        pnl_currency=_optional_text(value.get("pnl_currency"), "event.pnl_currency"),
        pnl_status=PnlStatus(_text(value.get("pnl_status"), "event.pnl_status")),
    )


def _encode_account(value: AccountRef) -> dict[str, Any]:
    return {
        "broker_id": value.broker_id,
        "environment": value.environment,
        "account_id": value.account_id,
    }


def _decode_account(value: dict[str, Any]) -> AccountRef:
    return AccountRef(
        broker_id=_text(value.get("broker_id"), "account.broker_id"),
        environment=_text(value.get("environment"), "account.environment"),
        account_id=_text(value.get("account_id"), "account.account_id"),
    )


def _datetime_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("Paper checkpoint timestamps must use UTC")
    return value.isoformat().replace("+00:00", "Z")


def _optional_datetime_text(value: datetime | None) -> str | None:
    return _datetime_text(value) if value is not None else None


def _datetime_value(value: Any, name: str) -> datetime:
    text = _text(value, name)
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError(f"{name} must use UTC")
    return parsed


def _optional_datetime_value(value: Any, name: str) -> datetime | None:
    return None if value is None else _datetime_value(value, name)


def _optional_decimal_text(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _decimal_value(value: Any, name: str) -> Decimal:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a decimal string")
    try:
        return Decimal(value)
    except Exception as exc:
        raise ValueError(f"{name} is not a valid decimal") from exc


def _optional_decimal_value(value: Any, name: str) -> Decimal | None:
    return None if value is None else _decimal_value(value, name)


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _text_allow_empty(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    return value


def _optional_text(value: Any, name: str) -> str | None:
    return None if value is None else _text(value, name)


def _integer(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    return value


def _boolean(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError("Paper checkpoint field must be a list")
    return value


def _items(value: dict[str, Any], name: str) -> list[Any]:
    return _list(value.get(name))
