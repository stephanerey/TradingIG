"""Conservative per-product projection of normalized market context."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from trading_ig_assistant.domain.ai_context import AIAnalysisStatus, MarketContextSnapshot
from trading_ig_assistant.domain.analysis import (
    DataState,
    ScoreBand,
    ScoreComponent,
    ScoreComponentName,
    SignalSide,
    StrategyId,
    StrategySignal,
)
from trading_ig_assistant.domain.macro_context import (
    ContextSeverity,
    DirectionalBias,
    EventRisk,
    MacroRibbonState,
    MarketRegime,
)
from trading_ig_assistant.domain.market_navigation import IGProductMarketBinding
from trading_ig_assistant.domain.products import (
    AssetClass,
    ProductDirection,
    TradableProduct,
)
from trading_ig_assistant.services.macro_context_service import MacroContextService


class ProductContextLevel(StrEnum):
    CATALYST = "catalyst"
    ALIGNED = "aligned"
    CAUTION = "caution"
    UNFAVORABLE = "unfavorable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProductContextProjection:
    """Display-safe context alignment; never a trade recommendation or probability."""

    level: ProductContextLevel
    components: tuple[str, ...]
    reason_codes: tuple[str, ...]
    provenance: tuple[str, ...]
    safety_veto: bool = False

    @property
    def label(self) -> str:
        return {
            ProductContextLevel.CATALYST: "CATALYSEUR",
            ProductContextLevel.ALIGNED: "ALIGNÉ",
            ProductContextLevel.CAUTION: "PRUDENCE",
            ProductContextLevel.UNFAVORABLE: "DÉFAVORABLE",
            ProductContextLevel.UNKNOWN: "INCONNU",
        }[self.level]

    @property
    def context_score(self) -> Decimal | None:
        return self.score_band.score

    @property
    def score_band(self) -> ScoreBand:
        return {
            ProductContextLevel.CATALYST: ScoreBand.EXCEPTIONAL,
            ProductContextLevel.ALIGNED: ScoreBand.FAVORABLE,
            ProductContextLevel.CAUTION: ScoreBand.CAUTION,
            ProductContextLevel.UNFAVORABLE: ScoreBand.UNFAVORABLE,
            ProductContextLevel.UNKNOWN: ScoreBand.UNKNOWN,
        }[self.level]

    @property
    def severity(self) -> ContextSeverity:
        return {
            ProductContextLevel.CATALYST: ContextSeverity.GREEN,
            ProductContextLevel.ALIGNED: ContextSeverity.GREEN,
            ProductContextLevel.CAUTION: ContextSeverity.YELLOW,
            ProductContextLevel.UNFAVORABLE: ContextSeverity.RED,
            ProductContextLevel.UNKNOWN: ContextSeverity.GRAY,
        }[self.level]

    @property
    def compact_text(self) -> str:
        score = f" {self.context_score}/100" if self.context_score is not None else ""
        return f"{self.label}{score} | {' | '.join(self.components)}"

    @property
    def tooltip(self) -> str:
        score = self.context_score if self.context_score is not None else "indisponible"
        lines = [
            "Contexte indicatif uniquement — ni recommandation, ni probabilité.",
            *self.components,
            f"État: {self.label}",
            f"Score contexte: {score}/100",
            f"Veto sécurité: {'oui' if self.safety_veto else 'non'}",
            f"Raisons: {', '.join(self.reason_codes) or 'aucune'}",
        ]
        if self.provenance:
            lines.append(f"Provenance: {', '.join(self.provenance)}")
        return "\n".join(lines)


class ProductContextProjectionService:
    """Project global/AI context relative to one product's directional exposure."""

    def project(
        self,
        product: TradableProduct,
        macro_state: MacroRibbonState,
        *,
        evaluated_at_utc: datetime,
        ai_snapshot: MarketContextSnapshot | None = None,
        qualified_event_signal: StrategySignal | None = None,
        ai_reference_binding: IGProductMarketBinding | None = None,
    ) -> ProductContextProjection:
        _require_utc(evaluated_at_utc)
        macro_state = MacroContextService().revalidate_state(macro_state, evaluated_at_utc)
        exposure = _exposure(product)
        bias_name, market_bias = _market_bias(product, macro_state)
        directional_assessments: list[ContextSeverity] = []
        reasons: list[str] = []
        components: list[str] = []

        if market_bias is DirectionalBias.UNKNOWN:
            components.append(f"{bias_name}:unknown")
            reasons.append("PRODUCT_MARKET_BIAS_UNKNOWN")
        elif exposure is None:
            components.append(f"{bias_name}:{market_bias.value}")
            reasons.append("PRODUCT_EXPOSURE_UNKNOWN")
        else:
            market_alignment = _direction_alignment(market_bias, exposure)
            directional_assessments.append(market_alignment)
            components.append(f"{bias_name}:{market_bias.value}")
            reasons.append(f"PRODUCT_MARKET_{market_alignment.value.upper()}")

        event_severity = _event_severity(macro_state.event_risk)
        components.append(f"event:{macro_state.event_risk.value}")
        if event_severity is ContextSeverity.GRAY:
            reasons.append("PRODUCT_EVENT_RISK_UNKNOWN")
        else:
            reasons.append(f"PRODUCT_EVENT_{event_severity.value.upper()}")

        ai_component, ai_severity, ai_reason = _project_ai(
            product,
            exposure,
            ai_snapshot,
            evaluated_at_utc,
            ai_reference_binding,
        )
        if (
            ai_snapshot is not None
            and ai_reference_binding is not None
            and ai_snapshot.instrument_id == ai_reference_binding.reference_epic
            and ai_reference_binding.product_epic == product.epic
            and product.epic != ai_snapshot.instrument_id
        ):
            ai_component += " (référence)"
            reasons.append("PRODUCT_AI_REFERENCE_MARKET")
        components.append(ai_component)
        reasons.append(ai_reason)
        if ai_severity is not ContextSeverity.GRAY:
            directional_assessments.append(ai_severity)

        catalyst = _qualified_catalyst(
            product,
            exposure,
            qualified_event_signal,
            evaluated_at_utc,
        )
        if (
            catalyst
            and event_severity is ContextSeverity.GREEN
            and not any(item is ContextSeverity.RED for item in directional_assessments)
        ):
            level = ProductContextLevel.CATALYST
            components.append("event_signal:confirmed")
            reasons.append("PRODUCT_EVENT_CATALYST_CONFIRMED")
        else:
            level = _combine(directional_assessments, event_severity)
            if qualified_event_signal is not None and not catalyst:
                reasons.append("PRODUCT_EVENT_CATALYST_NOT_QUALIFIED")
        safety_veto = event_severity is ContextSeverity.RED
        provenance = tuple(
            dict.fromkeys(
                (
                    *macro_state.provenance,
                    *(
                        ai_snapshot.provenance
                        if ai_snapshot is not None
                        and _ai_scope_applies(ai_snapshot, product, ai_reference_binding)
                        else ()
                    ),
                    *(
                        ("ai_scope:reference_market", *ai_reference_binding.provenance)
                        if ai_reference_binding is not None
                        and ai_snapshot is not None
                        and ai_snapshot.instrument_id == ai_reference_binding.reference_epic
                        and product.epic == ai_reference_binding.product_epic
                        and product.epic != ai_snapshot.instrument_id
                        else ()
                    ),
                    *(
                        qualified_event_signal.provenance
                        if catalyst and qualified_event_signal is not None
                        else ()
                    ),
                )
            )
        )
        return ProductContextProjection(
            level=level,
            components=tuple(components),
            reason_codes=tuple(dict.fromkeys(reasons)),
            provenance=provenance,
            safety_veto=safety_veto,
        )


def build_context_score_component(
    projection: ProductContextProjection,
    *,
    weight: Decimal = Decimal("15"),
) -> ScoreComponent:
    """Convert the human-approved context scale into one scanner ranking component."""

    return ScoreComponent(
        name=ScoreComponentName.CONTEXT,
        score=projection.context_score,
        weight=weight,
        reason_codes=projection.reason_codes,
        provenance=projection.provenance,
        veto=projection.safety_veto,
        band=projection.score_band,
    )


def _market_bias(
    product: TradableProduct,
    macro_state: MacroRibbonState,
) -> tuple[str, DirectionalBias]:
    normalized_name = _normalize(product.name)
    if "gold" in normalized_name or "or spot" in normalized_name:
        return "gold", macro_state.gold_bias
    if product.asset_class is AssetClass.INDICES:
        return "index", macro_state.index_bias
    if any(
        token in normalized_name
        for token in (
            "us tech",
            "nasdaq",
            "france 40",
            "germany 40",
            "dax",
            "wall street",
            "us 500",
            "ftse",
        )
    ):
        return "index", macro_state.index_bias
    return "market", _regime_bias(macro_state.regime)


def _regime_bias(regime: MarketRegime) -> DirectionalBias:
    if regime is MarketRegime.RISK_ON:
        return DirectionalBias.BULLISH
    if regime is MarketRegime.RISK_OFF:
        return DirectionalBias.BEARISH
    if regime is MarketRegime.NEUTRAL:
        return DirectionalBias.NEUTRAL
    return DirectionalBias.UNKNOWN


def _exposure(product: TradableProduct) -> int | None:
    if product.direction in {ProductDirection.BUY, ProductDirection.CALL}:
        return 1
    if product.direction in {ProductDirection.SELL, ProductDirection.PUT}:
        return -1
    normalized = f" {_normalize(product.name)} "
    if any(token in normalized for token in (" achat ", " buy ", " call ", " hauss")):
        return 1
    if any(token in normalized for token in (" vente ", " sell ", " put ", " baiss")):
        return -1
    return None


def _direction_alignment(bias: DirectionalBias, exposure: int) -> ContextSeverity:
    if bias is DirectionalBias.NEUTRAL:
        return ContextSeverity.YELLOW
    bias_direction = 1 if bias is DirectionalBias.BULLISH else -1
    return ContextSeverity.GREEN if bias_direction == exposure else ContextSeverity.RED


def _event_severity(event_risk: EventRisk) -> ContextSeverity:
    return {
        EventRisk.LOW: ContextSeverity.GREEN,
        EventRisk.MEDIUM: ContextSeverity.YELLOW,
        EventRisk.HIGH: ContextSeverity.RED,
        EventRisk.UNKNOWN: ContextSeverity.GRAY,
    }[event_risk]


def _project_ai(
    product: TradableProduct,
    exposure: int | None,
    snapshot: MarketContextSnapshot | None,
    evaluated_at_utc: datetime,
    ai_reference_binding: IGProductMarketBinding | None = None,
) -> tuple[str, ContextSeverity, str]:
    if snapshot is None:
        return "ai:inactive", ContextSeverity.GRAY, "PRODUCT_AI_INACTIVE"
    if not _ai_scope_applies(snapshot, product, ai_reference_binding):
        return "ai:not-applicable", ContextSeverity.GRAY, "PRODUCT_AI_SCOPE_MISMATCH"
    analysis = snapshot.ai_analysis
    if snapshot.generated_at_utc > evaluated_at_utc:
        return "ai:future", ContextSeverity.GRAY, "PRODUCT_AI_FROM_FUTURE"
    if snapshot.valid_until_utc <= evaluated_at_utc:
        return "ai:stale", ContextSeverity.GRAY, "PRODUCT_AI_STALE"
    if analysis.status is not AIAnalysisStatus.AVAILABLE:
        return "ai:unavailable", ContextSeverity.GRAY, "PRODUCT_AI_UNAVAILABLE"
    if analysis.event_risk is EventRisk.HIGH:
        return f"ai:{analysis.directional_bias.value}", ContextSeverity.RED, "PRODUCT_AI_HIGH_RISK"
    if exposure is None or analysis.directional_bias is DirectionalBias.UNKNOWN:
        return (
            f"ai:{analysis.directional_bias.value}",
            ContextSeverity.GRAY,
            "PRODUCT_AI_DIRECTION_UNKNOWN",
        )
    severity = _direction_alignment(analysis.directional_bias, exposure)
    if analysis.event_risk is EventRisk.MEDIUM and severity is ContextSeverity.GREEN:
        severity = ContextSeverity.YELLOW
    return (
        f"ai:{analysis.directional_bias.value}",
        severity,
        f"PRODUCT_AI_{severity.value.upper()}",
    )


def _ai_scope_applies(
    snapshot: MarketContextSnapshot,
    product: TradableProduct,
    binding: IGProductMarketBinding | None = None,
) -> bool:
    if snapshot.instrument_id in {"GLOBAL-MARKET-CONTEXT", product.epic}:
        return True
    return bool(
        binding is not None
        and binding.product_epic == product.epic
        and binding.reference_epic == snapshot.instrument_id
        and binding.provenance
    )


def _qualified_catalyst(
    product: TradableProduct,
    exposure: int | None,
    signal: StrategySignal | None,
    evaluated_at_utc: datetime,
) -> bool:
    if signal is None or exposure is None:
        return False
    expected_side = SignalSide.BUY if exposure > 0 else SignalSide.SELL
    return (
        signal.strategy_id == StrategyId.EVENT_DRIVEN.value
        and signal.instrument_id == product.epic
        and signal.data_state is DataState.READY
        and signal.side is expected_side
        and signal.generated_at_utc <= evaluated_at_utc < signal.valid_until_utc
        and "EVENT_PRICE_AND_CONTEXT_CONFIRMED" in signal.reason_codes
        and bool(signal.provenance)
    )


def _combine(
    directional_assessments: list[ContextSeverity],
    event_severity: ContextSeverity,
) -> ProductContextLevel:
    if event_severity is ContextSeverity.RED or ContextSeverity.RED in directional_assessments:
        return ProductContextLevel.UNFAVORABLE
    if not directional_assessments:
        return (
            ProductContextLevel.CAUTION
            if event_severity is ContextSeverity.YELLOW
            else ProductContextLevel.UNKNOWN
        )
    if ContextSeverity.YELLOW in directional_assessments or event_severity in {
        ContextSeverity.YELLOW,
        ContextSeverity.GRAY,
    }:
        return ProductContextLevel.CAUTION
    return ProductContextLevel.ALIGNED


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return " ".join(decomposed.lower().split())


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("evaluated_at_utc must use UTC")
