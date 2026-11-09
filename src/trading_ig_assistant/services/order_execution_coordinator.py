"""Risk-gated coordinator for the paper-only execution boundary."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from trading_ig_assistant.domain.adapter_contracts import (
    AccountRef,
    ExecutionResult,
    ExecutionStatus,
    OrderIntent,
)
from trading_ig_assistant.domain.positions import PaperFillAssumptions, PaperQuote
from trading_ig_assistant.domain.risk import (
    PortfolioRiskSnapshot,
    ResolvedRiskSettings,
    RiskDecision,
    RiskRequest,
)
from trading_ig_assistant.services.paper_broker import PaperBroker
from trading_ig_assistant.services.risk_engine import RiskEngine


@dataclass(frozen=True)
class PaperExecutionOutcome:
    risk_decision: RiskDecision
    execution_result: ExecutionResult


class PaperOrderExecutionCoordinator:
    """Only path that converts an approved local risk decision into a paper fill."""

    def __init__(self, risk_engine: RiskEngine, broker: PaperBroker) -> None:
        self._risk_engine = risk_engine
        self._broker = broker
        self._outcomes: dict[str, PaperExecutionOutcome] = {}
        self._intents: dict[str, OrderIntent] = {}
        self._lock = Lock()

    def execute(
        self,
        intent: OrderIntent,
        risk_request: RiskRequest,
        snapshot: PortfolioRiskSnapshot,
        *,
        assumptions: PaperFillAssumptions | None = None,
        settings: ResolvedRiskSettings | None = None,
    ) -> PaperExecutionOutcome:
        if (
            intent.intent_id != risk_request.intent_id
            or intent.account != risk_request.account
            or intent.underlying_id != risk_request.underlying_id
        ):
            raise ValueError("intent and risk request identity must match")
        with self._lock:
            cached = self._outcomes.get(intent.intent_id)
            if cached is not None:
                if self._intents[intent.intent_id] != intent:
                    raise ValueError("intent_id already executed with different content")
                return cached
            decision = self._risk_engine.evaluate_and_reserve(
                risk_request,
                snapshot,
                settings,
            )
            if not decision.approved:
                outcome = PaperExecutionOutcome(
                    risk_decision=decision,
                    execution_result=ExecutionResult(
                        intent_id=intent.intent_id,
                        account=intent.account,
                        status=ExecutionStatus.REJECTED,
                        message="RISK_REJECTED:"
                        + ",".join(reason.value for reason in decision.reasons),
                    ),
                )
                self._intents[intent.intent_id] = intent
                self._outcomes[intent.intent_id] = outcome
                return outcome
            self._broker.authorize(intent, decision, assumptions)
            result = self._broker.submit(intent)
            if result.status is not ExecutionStatus.CONFIRMED:
                self._risk_engine.release(intent.intent_id)
            outcome = PaperExecutionOutcome(risk_decision=decision, execution_result=result)
            self._intents[intent.intent_id] = intent
            self._outcomes[intent.intent_id] = outcome
            return outcome

    def process_quote(self, quote: PaperQuote) -> tuple[ExecutionResult, ...]:
        """Apply one quote and release risk reservations for confirmed Paper exits."""

        open_intents_by_position = {
            position.position_id: position.intent_id
            for account in self._broker.accounts()
            for position in self._broker.positions(account)
        }
        results = self._broker.process_quote(quote)
        for result in results:
            if result.status is not ExecutionStatus.CONFIRMED:
                continue
            intent_id = open_intents_by_position.get(result.broker_reference or "")
            if intent_id is not None:
                self._risk_engine.release(intent_id)
        return results

    def close(self, account: AccountRef, position_id: str) -> ExecutionResult:
        position = next(
            (
                candidate
                for candidate in self._broker.positions(account)
                if candidate.position_id == position_id
            ),
            None,
        )
        if position is None:
            return self._broker.close(account, position_id)
        result = self._broker.close(account, position_id)
        if result.status is ExecutionStatus.CONFIRMED:
            self._risk_engine.release(position.intent_id)
        return result
