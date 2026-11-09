from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.adapters.credentials import IGCredentials
from trading_ig_assistant.adapters.ig_demo_probe import (
    DemoProbeRejectedError,
    IGDemoExecutionProbeAdapter,
)
from trading_ig_assistant.adapters.ig_rest import HttpResponse, LiveTradingDisabledError
from trading_ig_assistant.domain.adapter_contracts import AccountRef, OrderDirection
from trading_ig_assistant.domain.supervised_demo import (
    DemoGateDecision,
    DemoMutationAuthorization,
    DemoMutationOperation,
    DemoProbePlan,
    DemoProductFamily,
    fingerprint_account,
)

NOW = datetime(2026, 10, 23, 17, 0, tzinfo=UTC)
ACCOUNT = AccountRef(broker_id="ig", environment="demo", account_id="DEMO-ACCOUNT")


class ProbeHttpClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def request(self, method, url, *, headers, json_body=None, timeout):
        self.requests.append(
            {"method": method, "url": url, "headers": headers, "json_body": json_body}
        )
        if url.endswith("/session") and method == "POST":
            return HttpResponse(
                200,
                {"CST": "cst", "X-SECURITY-TOKEN": "token"},
                {"currentAccountId": ACCOUNT.account_id},
            )
        if "/confirms/" in url:
            reference = url.rsplit("/", 1)[-1]
            return HttpResponse(
                200,
                {},
                {
                    "dealReference": reference,
                    "dealId": "DEAL-1",
                    "dealStatus": "ACCEPTED",
                    "direction": "BUY",
                    "epic": "IX.D.SYNTHETIC.IFD.IP",
                    "level": 100,
                    "stopLevel": 94,
                    "size": 0.2,
                },
            )
        if (
            url.endswith("/positions/otc")
            and method == "POST"
            and headers.get("_method") == "DELETE"
        ):
            return HttpResponse(200, {}, {"dealReference": "CLOSE-1"})
        if url.endswith("/positions/otc") and method == "POST":
            return HttpResponse(200, {}, {"dealReference": json_body["dealReference"]})
        if "/positions/otc/" in url and method == "PUT":
            return HttpResponse(200, {}, {"dealReference": "UPDATE-1"})
        if url.endswith("/positions") and method == "GET":
            return HttpResponse(200, {}, {"positions": []})
        raise AssertionError(f"Unexpected request: {method} {url}")


def _plan() -> DemoProbePlan:
    return DemoProbePlan(
        intent_id="DEMO-PROBE-1",
        account_fingerprint=fingerprint_account(ACCOUNT),
        product_id="IX.D.SYNTHETIC.IFD.IP",
        product_family=DemoProductFamily.CFD,
        direction=OrderDirection.BUY,
        size=Decimal("0.2"),
        expiry="-",
        initial_stop_distance=Decimal("6"),
        tightened_stop_distance=Decimal("4.5"),
        currency="USD",
    )


def _authorization() -> DemoMutationAuthorization:
    return DemoMutationAuthorization(
        authorization_id="AUTH-1",
        plan=_plan(),
        allowed_operations=tuple(DemoMutationOperation),
        granted_at_utc=NOW,
        expires_at_utc=NOW + timedelta(minutes=10),
    )


def _decision(operation: DemoMutationOperation) -> DemoGateDecision:
    return DemoGateDecision(
        eligible=True,
        authorization_id="AUTH-1",
        intent_id="DEMO-PROBE-1",
        operation=operation,
    )


def _adapter(
    client: ProbeHttpClient | None = None,
) -> tuple[IGDemoExecutionProbeAdapter, ProbeHttpClient]:
    http = client or ProbeHttpClient()
    adapter = IGDemoExecutionProbeAdapter(
        authorization=_authorization(),
        http_client=http,
        now_provider=lambda: NOW + timedelta(seconds=30),
    )
    adapter.login(IGCredentials("demo-user", "password", "api-key"))
    return adapter, http


def test_create_is_exactly_scoped_and_consumed_before_retry() -> None:
    adapter, http = _adapter()

    acknowledgement = adapter.create_otc_position(
        _plan(), _decision(DemoMutationOperation.CREATE_POSITION)
    )

    assert acknowledgement.deal_reference == "DEMO-PROBE-1"
    request = http.requests[-1]
    assert request["method"] == "POST"
    assert request["url"].startswith("https://demo-api.ig.com/")
    assert request["headers"]["VERSION"] == "2"
    assert request["json_body"] == {
        "currencyCode": "USD",
        "dealReference": "DEMO-PROBE-1",
        "direction": "BUY",
        "epic": "IX.D.SYNTHETIC.IFD.IP",
        "expiry": "-",
        "forceOpen": True,
        "guaranteedStop": False,
        "orderType": "MARKET",
        "size": 0.2,
        "stopDistance": 6.0,
        "timeInForce": "FILL_OR_KILL",
        "trailingStop": False,
    }
    with pytest.raises(DemoProbeRejectedError, match="already consumed"):
        adapter.create_otc_position(_plan(), _decision(DemoMutationOperation.CREATE_POSITION))


def test_confirm_then_update_and_close_only_the_created_deal() -> None:
    adapter, http = _adapter()
    adapter.create_otc_position(_plan(), _decision(DemoMutationOperation.CREATE_POSITION))
    confirmation = adapter.get_deal_confirmation("DEMO-PROBE-1")

    adapter.update_position(
        confirmation.deal_id or "",
        stop_level=Decimal("95.5"),
        gate_decision=_decision(DemoMutationOperation.UPDATE_STOP),
    )
    adapter.close_position(
        confirmation.deal_id or "",
        gate_decision=_decision(DemoMutationOperation.CLOSE_POSITION),
    )

    assert confirmation.accepted is True
    update = http.requests[-2]
    close = http.requests[-1]
    assert update["method"] == "PUT"
    assert update["json_body"] == {
        "guaranteedStop": False,
        "stopLevel": 95.5,
        "trailingStop": False,
    }
    assert close["method"] == "POST"
    assert close["headers"]["_method"] == "DELETE"
    assert close["json_body"]["direction"] == "SELL"
    assert close["json_body"]["size"] == 0.2


def test_probe_rejects_wrong_account_expiry_wrong_operation_and_working_orders() -> None:
    adapter, _ = _adapter()
    adapter._session = replace(adapter.session, current_account_id="OTHER-DEMO")
    with pytest.raises(DemoProbeRejectedError, match="account"):
        adapter.create_otc_position(_plan(), _decision(DemoMutationOperation.CREATE_POSITION))

    expired = IGDemoExecutionProbeAdapter(
        authorization=_authorization(),
        http_client=ProbeHttpClient(),
        now_provider=lambda: NOW + timedelta(hours=1),
    )
    expired.login(IGCredentials("demo-user", "password", "api-key"))
    with pytest.raises(DemoProbeRejectedError, match="expired"):
        expired.create_otc_position(_plan(), _decision(DemoMutationOperation.CREATE_POSITION))

    adapter, _ = _adapter()
    with pytest.raises(DemoProbeRejectedError, match="decision"):
        adapter.create_otc_position(_plan(), _decision(DemoMutationOperation.UPDATE_STOP))
    with pytest.raises(LiveTradingDisabledError):
        adapter.create_working_order({})


def test_position_change_requires_a_confirmed_deal() -> None:
    adapter, _ = _adapter()
    with pytest.raises(DemoProbeRejectedError, match="confirmed deal"):
        adapter.update_position(
            "UNRELATED",
            stop_level=Decimal("95.5"),
            gate_decision=_decision(DemoMutationOperation.UPDATE_STOP),
        )
    with pytest.raises(DemoProbeRejectedError, match="confirmed deal"):
        adapter.close_position(
            "UNRELATED", gate_decision=_decision(DemoMutationOperation.CLOSE_POSITION)
        )


def test_reconciled_exact_position_can_be_bound_for_one_close() -> None:
    adapter, http = _adapter()
    deal_id = adapter.bind_reconciled_position(
        {
            "market": {"epic": "IX.D.SYNTHETIC.IFD.IP"},
            "position": {"dealId": "DEAL-1", "direction": "BUY", "size": 0.2},
        }
    )

    adapter.close_position(
        deal_id, gate_decision=_decision(DemoMutationOperation.CLOSE_POSITION)
    )

    assert http.requests[-1]["method"] == "POST"
    assert http.requests[-1]["headers"]["_method"] == "DELETE"
    with pytest.raises(DemoProbeRejectedError, match="already consumed"):
        adapter.close_position(
            deal_id, gate_decision=_decision(DemoMutationOperation.CLOSE_POSITION)
        )


def test_reconciliation_rejects_a_nonmatching_position() -> None:
    adapter, _ = _adapter()
    with pytest.raises(DemoProbeRejectedError, match="does not exactly match"):
        adapter.bind_reconciled_position(
            {
                "market": {"epic": "OTHER"},
                "position": {"dealId": "DEAL-2", "direction": "BUY", "size": 0.2},
            }
        )
