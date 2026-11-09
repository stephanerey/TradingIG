"""Single-use IG DEMO execution path for an explicitly authorized probe."""

from __future__ import annotations

import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from trading_ig_assistant.adapters.ig_rest import (
    IG_DEMO_BASE_URL,
    IGAPIError,
    IGRestAdapter,
    LiveTradingDisabledError,
)
from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.domain.adapter_contracts import OrderDirection
from trading_ig_assistant.domain.supervised_demo import (
    DemoGateDecision,
    DemoMutationAuthorization,
    DemoMutationOperation,
    DemoProbePlan,
    fingerprint_account,
)


class DemoProbeRejectedError(LiveTradingDisabledError):
    """Raised before HTTP when a bounded DEMO probe invariant is not satisfied."""


@dataclass(frozen=True)
class IGDealAcknowledgement:
    deal_reference: str


@dataclass(frozen=True)
class IGDealConfirmation:
    deal_reference: str
    deal_id: str | None
    deal_status: str
    reason: str | None
    direction: str | None
    epic: str | None
    level: Decimal | None
    stop_level: Decimal | None
    size: Decimal | None

    @property
    def accepted(self) -> bool:
        return self.deal_status.upper() == "ACCEPTED" and bool(self.deal_id)


class IGDemoExecutionProbeAdapter(IGRestAdapter):
    """Narrow adapter that can execute one pre-authorized DEMO create/update/close sequence.

    The environment is fixed to DEMO. Each mutation is consumed before its HTTP request, so an
    ambiguous network result can never cause an automatic resubmission.
    """

    def __init__(
        self,
        *,
        authorization: DemoMutationAuthorization,
        http_client: Any | None = None,
        timeout: float = 10.0,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__(
            environment=IGEnvironment.DEMO,
            http_client=http_client,
            timeout=timeout,
            read_only=False,
        )
        self._authorization = authorization
        self._now_provider = now_provider or (lambda: datetime.now(UTC))
        self._consumed_operations: set[DemoMutationOperation] = set()
        self._confirmed_deal_id: str | None = None

    @property
    def base_url(self) -> str:
        return IG_DEMO_BASE_URL

    def get_open_positions(self) -> tuple[dict[str, Any], ...]:
        response = self._request("GET", "/positions", version="2")
        return tuple(item for item in response.body.get("positions", []) if isinstance(item, dict))

    def get_deal_confirmation(self, deal_reference: str) -> IGDealConfirmation:
        encoded_reference = urllib.parse.quote(deal_reference, safe="")
        response = self._request("GET", f"/confirms/{encoded_reference}", version="1")
        body = response.body
        confirmation = IGDealConfirmation(
            deal_reference=str(body.get("dealReference") or deal_reference),
            deal_id=_optional_string(body.get("dealId")),
            deal_status=str(body.get("dealStatus") or "UNKNOWN"),
            reason=_optional_string(body.get("reason")),
            direction=_optional_string(body.get("direction")),
            epic=_optional_string(body.get("epic")),
            level=_optional_decimal(body.get("level")),
            stop_level=_optional_decimal(body.get("stopLevel")),
            size=_optional_decimal(body.get("size")),
        )
        if (
            confirmation.accepted
            and confirmation.deal_reference == self._authorization.plan.intent_id
        ):
            self._confirmed_deal_id = confirmation.deal_id
        return confirmation

    def bind_reconciled_position(self, item: dict[str, Any]) -> str:
        """Bind one read-back position that exactly matches the authorized probe plan.

        This recovery path does not submit anything. It is used only after a read-only positions
        query proves that an earlier ambiguous close left the exact probe position open.
        """

        if DemoMutationOperation.CLOSE_POSITION in self._consumed_operations:
            raise DemoProbeRejectedError("The IG DEMO close operation was already consumed.")
        market = item.get("market", {})
        position = item.get("position", {})
        plan = self._authorization.plan
        deal_id = str(position.get("dealId") or "")
        try:
            size = Decimal(str(position.get("size")))
        except (ValueError, ArithmeticError):
            size = Decimal("-1")
        if (
            not deal_id
            or market.get("epic") != plan.product_id
            or position.get("direction") != plan.direction.value
            or size != plan.size
        ):
            raise DemoProbeRejectedError(
                "The reconciled position does not exactly match the authorized probe."
            )
        self._confirmed_deal_id = deal_id
        return deal_id

    def create_otc_position(
        self,
        plan: DemoProbePlan,
        gate_decision: DemoGateDecision,
    ) -> IGDealAcknowledgement:
        self._consume(DemoMutationOperation.CREATE_POSITION, plan, gate_decision)
        response = self._request(
            "POST",
            "/positions/otc",
            version="2",
            json_body={
                "currencyCode": plan.currency,
                "dealReference": plan.intent_id,
                "direction": plan.direction.value,
                "epic": plan.product_id,
                "expiry": plan.expiry,
                "forceOpen": True,
                "guaranteedStop": False,
                "orderType": "MARKET",
                "size": float(plan.size),
                "stopDistance": float(plan.initial_stop_distance),
                "timeInForce": "FILL_OR_KILL",
                "trailingStop": False,
            },
        )
        deal_reference = str(response.body.get("dealReference") or "")
        if deal_reference != plan.intent_id:
            raise IGAPIError(
                "IG DEMO acknowledgement did not preserve the expected deal reference."
            )
        return IGDealAcknowledgement(deal_reference=deal_reference)

    def update_position(
        self,
        deal_id: str,
        *,
        stop_level: Decimal,
        gate_decision: DemoGateDecision,
    ) -> IGDealAcknowledgement:
        plan = self._authorization.plan
        self._require_confirmed_deal(deal_id)
        self._consume(DemoMutationOperation.UPDATE_STOP, plan, gate_decision)
        encoded_deal_id = urllib.parse.quote(deal_id, safe="")
        response = self._request(
            "PUT",
            f"/positions/otc/{encoded_deal_id}",
            version="2",
            json_body={
                "guaranteedStop": False,
                "stopLevel": float(stop_level),
                "trailingStop": False,
            },
        )
        return _acknowledgement_from_response(response.body)

    def close_position(
        self,
        deal_id: str,
        *,
        gate_decision: DemoGateDecision,
    ) -> IGDealAcknowledgement:
        plan = self._authorization.plan
        self._require_confirmed_deal(deal_id)
        self._consume(DemoMutationOperation.CLOSE_POSITION, plan, gate_decision)
        close_direction = (
            OrderDirection.SELL if plan.direction is OrderDirection.BUY else OrderDirection.BUY
        )
        response = self._request(
            "POST",
            "/positions/otc",
            version="1",
            extra_headers={"_method": "DELETE"},
            json_body={
                "dealId": deal_id,
                "direction": close_direction.value,
                "orderType": "MARKET",
                "size": float(plan.size),
                "timeInForce": "FILL_OR_KILL",
            },
        )
        return _acknowledgement_from_response(response.body)

    def create_working_order(self, *_args: Any, **_kwargs: Any) -> None:
        raise LiveTradingDisabledError("Working orders remain disabled for the DEMO probe.")

    def _consume(
        self,
        operation: DemoMutationOperation,
        plan: DemoProbePlan,
        decision: DemoGateDecision,
    ) -> None:
        now = self._now_provider()
        session = self.session
        if self.environment is not IGEnvironment.DEMO or self.base_url != IG_DEMO_BASE_URL:
            raise DemoProbeRejectedError("The supervised probe is restricted to IG DEMO.")
        if session is None or not session.current_account_id:
            raise DemoProbeRejectedError("An authenticated IG DEMO account is required.")
        if fingerprint_account(
            _account_ref(session.current_account_id)
        ) != self._authorization.plan.account_fingerprint:
            raise DemoProbeRejectedError(
                "The active IG DEMO account does not match the authorization."
            )
        if plan != self._authorization.plan:
            raise DemoProbeRejectedError("The requested plan does not match the authorization.")
        if now > self._authorization.expires_at_utc:
            raise DemoProbeRejectedError("The IG DEMO authorization has expired.")
        if (
            not decision.eligible
            or decision.authorization_id != self._authorization.authorization_id
            or decision.intent_id != plan.intent_id
            or decision.operation is not operation
        ):
            raise DemoProbeRejectedError(
                "The IG DEMO gate decision does not authorize this operation."
            )
        if operation not in self._authorization.allowed_operations:
            raise DemoProbeRejectedError("The IG DEMO operation was not authorized.")
        if operation in self._consumed_operations:
            raise DemoProbeRejectedError("The IG DEMO operation was already consumed.")
        self._consumed_operations.add(operation)

    def _require_confirmed_deal(self, deal_id: str) -> None:
        if not deal_id or deal_id != self._confirmed_deal_id:
            raise DemoProbeRejectedError(
                "Only the confirmed deal created by this probe may be changed."
            )


def _account_ref(account_id: str):
    from trading_ig_assistant.domain.adapter_contracts import AccountRef

    return AccountRef(broker_id="ig", environment="demo", account_id=account_id)


def _acknowledgement_from_response(body: dict[str, Any]) -> IGDealAcknowledgement:
    deal_reference = str(body.get("dealReference") or "")
    if not deal_reference:
        raise IGAPIError("IG DEMO acknowledgement did not include a deal reference.")
    return IGDealAcknowledgement(deal_reference=deal_reference)


def _optional_string(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (ValueError, ArithmeticError):
        return None
