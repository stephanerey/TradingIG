"""Run the single explicitly authorized IG DEMO execution probe.

This script is intentionally not wired into the GUI. It requires an explicit command-line guard,
loads DEMO credentials from the existing secure store, and never accepts a LIVE environment.
"""

from __future__ import annotations

import argparse
import time
from datetime import UTC, datetime, timedelta
from decimal import ROUND_FLOOR, Decimal

from trading_ig_assistant.adapters.credentials import build_default_credential_store
from trading_ig_assistant.adapters.ig_demo_probe import (
    IGDealConfirmation,
    IGDemoExecutionProbeAdapter,
)
from trading_ig_assistant.adapters.ig_rest import IGAPIError
from trading_ig_assistant.app.config import IGEnvironment, default_config_path, load_config
from trading_ig_assistant.domain.adapter_contracts import (
    AccountRef,
    OrderDirection,
    OrderIntent,
)
from trading_ig_assistant.domain.risk import (
    AccountRiskState,
    PortfolioRiskSnapshot,
    RiskAction,
    RiskRequest,
)
from trading_ig_assistant.domain.supervised_demo import (
    DemoConfirmationSnapshot,
    DemoMutationAuthorization,
    DemoMutationOperation,
    DemoProbePlan,
    DemoProductFamily,
    fingerprint_account,
)
from trading_ig_assistant.services.risk_engine import RiskEngine
from trading_ig_assistant.services.supervised_demo_gate import SupervisedDemoGate

EXECUTION_GUARD = "AUTHORIZED-IG-DEMO-ONLY"
PRODUCT_EPIC = "IX.D.CAC.IMF.IP"
PRODUCT_NAME = "France 40 au comptant (1 EUR)"
PRODUCT_CURRENCY = "EUR"
SIZE = Decimal("0.5")
INITIAL_STOP_DISTANCE = Decimal("6")
TIGHTENED_STOP_DISTANCE = Decimal("4.5")
SCENARIO_SLIPPAGE_POINTS = Decimal("1")
CONFIRM_TIMEOUT_SECONDS = 18


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-demo-probe", required=True)
    args = parser.parse_args()
    if args.execute_demo_probe != EXECUTION_GUARD:
        print("REFUSED: the exact IG DEMO execution guard was not supplied.")
        return 2

    config = load_config(default_config_path())
    profile = config.connection_profiles[IGEnvironment.DEMO]
    credential_store = build_default_credential_store()
    credentials = (
        credential_store.load_profile(IGEnvironment.DEMO.value, profile.identifier)
        if credential_store is not None and profile.identifier
        else None
    )
    if credentials is None:
        print("REFUSED: DEMO credentials are unavailable in the secure store.")
        return 2
    if not profile.selected_account_id:
        print("REFUSED: select and save an exact DEMO CFD account in the GUI first.")
        return 2

    now = datetime.now(UTC)
    intent_id = f"CDXDEMO{now:%Y%m%d%H%M%S}"
    account_ref = AccountRef(
        broker_id="ig",
        environment="demo",
        account_id=profile.selected_account_id,
    )
    plan = _plan(intent_id, account_ref)
    authorization = _authorization(now, plan)
    adapter = IGDemoExecutionProbeAdapter(authorization=authorization)
    risk_engine = RiskEngine()
    opened = False
    confirmed_deal_id: str | None = None
    exit_code = 1

    try:
        session = adapter.login(credentials)
        accounts = adapter.get_accounts()
        account = _select_cfd_account(
            accounts, profile.selected_account_id, session.current_account_id
        )
        if account is None:
            print("REFUSED: no unambiguous DEMO CFD account is available.")
            return 2
        if session.current_account_id != account.account_id:
            session = adapter.switch_account(account.account_id)
        if session.current_account_id != account.account_id:
            print("REFUSED: IG did not confirm the selected DEMO CFD account.")
            return 2

        if account.account_id != account_ref.account_id:
            print("REFUSED: the configured DEMO account does not match the selected CFD account.")
            return 2

        positions = adapter.get_open_positions()
        if positions:
            print("REFUSED: the selected DEMO account already has an open position.")
            return 2

        market = adapter.get_market_details(PRODUCT_EPIC).raw
        preflight = _market_preflight(market)
        if preflight is None:
            print("REFUSED: the exact CFD is not currently TRADEABLE with expected metadata.")
            return 2
        bid, offer, value_per_point, minimum_size, minimum_stop = preflight
        if SIZE != minimum_size or INITIAL_STOP_DISTANCE <= minimum_stop:
            print("REFUSED: live IG dealing rules no longer match the bounded plan.")
            return 2

        risk_snapshot = _risk_snapshot(account_ref, account)
        spread_cost = (offer - bid) * value_per_point * SIZE
        stop_loss = INITIAL_STOP_DISTANCE * value_per_point * SIZE
        slippage = SCENARIO_SLIPPAGE_POINTS * value_per_point * SIZE
        risk_request = RiskRequest(
            intent_id=intent_id,
            account=account_ref,
            underlying_id="FRANCE-40",
            action=RiskAction.OPEN,
            estimated_stop_loss=stop_loss,
            anticipated_costs=spread_cost,
            scenario_slippage=slippage,
            price_fresh=True,
            market_open=True,
            product_supported=True,
        )
        risk_decision = risk_engine.evaluate_and_reserve(risk_request, risk_snapshot)
        if not risk_decision.approved:
            reasons = ",".join(reason.value for reason in risk_decision.reasons)
            print(f"REFUSED: independent risk engine rejected the probe ({reasons}).")
            return 2

        expires = now + timedelta(minutes=5)
        confirmation_snapshot = DemoConfirmationSnapshot(
            plan=plan,
            created_at_utc=now,
            expires_at_utc=expires,
        )
        intent = OrderIntent(
            intent_id=intent_id,
            account=account_ref,
            product_id=PRODUCT_EPIC,
            underlying_id="FRANCE-40",
            direction=OrderDirection.BUY,
            quantity=SIZE,
            requested_stop=None,
            requested_target=None,
            requested_ko=None,
            signal_id=None,
            expires_at_utc=expires,
        )
        gate = SupervisedDemoGate()
        create_gate = gate.evaluate_probe(
            intent=intent,
            confirmation=confirmation_snapshot,
            authorization=authorization,
            risk_decision=risk_decision,
            operation=DemoMutationOperation.CREATE_POSITION,
            now_utc=datetime.now(UTC),
            kill_switch_active=False,
        )
        if not create_gate.eligible:
            print("REFUSED: the supervised DEMO gate rejected the opening.")
            return 2

        print(
            "PLAN: IG DEMO only | CFD France 40 cash (1 EUR) | BUY | size 0.5 | "
            "stop 6 points | tighten to 4.5 points | immediate close"
        )
        print(
            "RISK: "
            f"estimated={risk_decision.estimated_loss_reference:.2f} EUR | "
            f"budget={risk_decision.budget_reference:.2f} EUR | "
            "open_positions=0"
        )

        try:
            acknowledgement = adapter.create_otc_position(plan, create_gate)
        except IGAPIError:
            acknowledgement = None
            print("OPEN: acknowledgement ambiguous; reconciling by immutable reference.")
        create_reference = acknowledgement.deal_reference if acknowledgement else intent_id
        created = _poll_confirmation(adapter, create_reference)
        if created is None:
            print("UNKNOWN: opening could not be confirmed; no blind retry was attempted.")
            return 3
        if not created.accepted:
            print(f"OPEN: rejected ({created.reason or 'unspecified'}).")
            return 2
        opened = True
        confirmed_deal_id = created.deal_id
        print("OPEN: ACCEPTED and confirmed.")

        refreshed_market = adapter.get_market_details(PRODUCT_EPIC).raw
        tightened_stop = _tightened_stop_level(refreshed_market, created)
        if tightened_stop is None:
            print("STOP: no safe tighter level is available; proceeding to immediate close.")
        else:
            reduce_decision = risk_engine.evaluate(
                RiskRequest(
                    intent_id=intent_id,
                    account=account_ref,
                    underlying_id="FRANCE-40",
                    action=RiskAction.REDUCE,
                ),
                risk_snapshot,
            )
            update_gate = gate.evaluate_probe(
                intent=intent,
                confirmation=confirmation_snapshot,
                authorization=authorization,
                risk_decision=reduce_decision,
                operation=DemoMutationOperation.UPDATE_STOP,
                now_utc=datetime.now(UTC),
                kill_switch_active=False,
            )
            try:
                updated_ack = adapter.update_position(
                    confirmed_deal_id or "",
                    stop_level=tightened_stop,
                    gate_decision=update_gate,
                )
                updated = _poll_confirmation(adapter, updated_ack.deal_reference)
            except IGAPIError:
                updated = None
            if updated is not None and updated.accepted:
                print("STOP: ACCEPTED and confirmed at the tighter distance.")
            elif updated is not None:
                print(f"STOP: rejected ({updated.reason or 'unspecified'}); closing immediately.")
            else:
                print("STOP: UNKNOWN after reconciliation; closing immediately.")

        close_decision = risk_engine.evaluate(
            RiskRequest(
                intent_id=intent_id,
                account=account_ref,
                underlying_id="FRANCE-40",
                action=RiskAction.CLOSE,
            ),
            risk_snapshot,
        )
        close_gate = gate.evaluate_probe(
            intent=intent,
            confirmation=confirmation_snapshot,
            authorization=authorization,
            risk_decision=close_decision,
            operation=DemoMutationOperation.CLOSE_POSITION,
            now_utc=datetime.now(UTC),
            kill_switch_active=False,
        )
        try:
            close_ack = adapter.close_position(
                confirmed_deal_id or "", gate_decision=close_gate
            )
            closed = _poll_confirmation(adapter, close_ack.deal_reference)
        except IGAPIError:
            closed = None
        if closed is None:
            print("UNKNOWN: close could not be confirmed; manual DEMO reconciliation is required.")
            return 3
        if not closed.accepted:
            print(f"CLOSE: rejected ({closed.reason or 'unspecified'}); manual action required.")
            return 3
        remaining = adapter.get_open_positions()
        matching_remaining = tuple(
            position
            for position in remaining
            if position.get("position", {}).get("dealId") == confirmed_deal_id
        )
        if matching_remaining:
            print("UNKNOWN: close was accepted but the position is still listed.")
            return 3
        opened = False
        print("CLOSE: ACCEPTED, confirmed, and absent from open DEMO positions.")
        print("RESULT: bounded IG DEMO probe completed; no LIVE endpoint was used.")
        exit_code = 0
        return exit_code
    finally:
        risk_engine.release(intent_id)
        try:
            adapter.logout()
        except IGAPIError:
            pass
        if opened and confirmed_deal_id:
            print("ALERT: a confirmed DEMO position may remain open; inspect IG DEMO manually.")


def _plan(intent_id: str, account: AccountRef) -> DemoProbePlan:
    return DemoProbePlan(
        intent_id=intent_id,
        account_fingerprint=fingerprint_account(account),
        product_id=PRODUCT_EPIC,
        product_family=DemoProductFamily.CFD,
        direction=OrderDirection.BUY,
        size=SIZE,
        expiry="-",
        initial_stop_distance=INITIAL_STOP_DISTANCE,
        tightened_stop_distance=TIGHTENED_STOP_DISTANCE,
        currency=PRODUCT_CURRENCY,
    )


def _authorization(now: datetime, plan: DemoProbePlan) -> DemoMutationAuthorization:
    return DemoMutationAuthorization(
        authorization_id="USER-20261023-BOUNDED-DEMO",
        plan=plan,
        allowed_operations=tuple(DemoMutationOperation),
        granted_at_utc=now,
        expires_at_utc=now + timedelta(minutes=8),
    )


def _select_cfd_account(accounts, configured_id: str | None, current_id: str | None):
    candidates = [account for account in accounts if str(account.account_type).upper() == "CFD"]
    for requested_id in (configured_id, current_id):
        match = next(
            (account for account in candidates if account.account_id == requested_id),
            None,
        )
        if match is not None:
            return match
    preferred = [account for account in candidates if account.preferred]
    if len(preferred) == 1:
        return preferred[0]
    return candidates[0] if len(candidates) == 1 else None


def _market_preflight(raw: dict):
    instrument = raw.get("instrument", {})
    rules = raw.get("dealingRules", {})
    snapshot = raw.get("snapshot", {})
    currencies = instrument.get("currencies") or []
    if (
        instrument.get("epic") != PRODUCT_EPIC
        or str(instrument.get("type")).upper() != "INDICES"
        or str(instrument.get("expiry")) != "-"
        or not currencies
        or currencies[0].get("code") != PRODUCT_CURRENCY
        or str(snapshot.get("marketStatus")).upper() != "TRADEABLE"
    ):
        return None
    try:
        return (
            Decimal(str(snapshot["bid"])),
            Decimal(str(snapshot["offer"])),
            Decimal(str(instrument["valueOfOnePip"])),
            Decimal(str(rules["minDealSize"]["value"])),
            Decimal(str(rules["minNormalStopOrLimitDistance"]["value"])),
        )
    except (KeyError, TypeError, ValueError, ArithmeticError):
        return None


def _risk_snapshot(account_ref: AccountRef, account) -> PortfolioRiskSnapshot:
    if (
        account.currency != "EUR"
        or account.balance is None
        or account.available is None
        or account.profit_loss is None
    ):
        raise RuntimeError("DEMO account risk data is incomplete")
    balance = Decimal(str(account.balance))
    available = Decimal(str(account.available))
    return PortfolioRiskSnapshot(
        reference_currency="EUR",
        accounts=(
            AccountRiskState(
                account=account_ref,
                currency="EUR",
                equity_reference_day=balance,
                equity_current=min(balance, available),
                daily_net_pnl=Decimal(str(account.profit_loss)),
                confirmed=True,
                active_for_opening=True,
            ),
        ),
        open_exposures=(),
        exposure_complete=True,
    )


def _tightened_stop_level(raw: dict, created: IGDealConfirmation) -> Decimal | None:
    preflight = _market_preflight(raw)
    if preflight is None or created.stop_level is None:
        return None
    bid, _offer, _value_per_point, _minimum_size, minimum_stop = preflight
    if TIGHTENED_STOP_DISTANCE <= minimum_stop:
        return None
    candidate = (bid - TIGHTENED_STOP_DISTANCE).quantize(
        Decimal("0.1"), rounding=ROUND_FLOOR
    )
    if candidate <= created.stop_level:
        return None
    return candidate


def _poll_confirmation(
    adapter: IGDemoExecutionProbeAdapter,
    deal_reference: str,
) -> IGDealConfirmation | None:
    deadline = time.monotonic() + CONFIRM_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            confirmation = adapter.get_deal_confirmation(deal_reference)
        except IGAPIError:
            time.sleep(0.7)
            continue
        if confirmation.deal_status.upper() in {"ACCEPTED", "REJECTED"}:
            return confirmation
        time.sleep(0.7)
    return None


if __name__ == "__main__":
    raise SystemExit(main())
