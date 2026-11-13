"""Read-only eligibility projection for an exact-product Paper ticket."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from trading_ig_assistant.app.projections.catalogue import ProductRowVM
from trading_ig_assistant.app.projections.common import Availability
from trading_ig_assistant.domain.market_data import QUOTE_FRESHNESS_SECONDS
from trading_ig_assistant.domain.market_navigation import IGProductMarketBinding


@dataclass(frozen=True)
class PaperTicketPreparationVM:
    product_epic: str
    product_name: str
    product_type: str
    product_direction: str
    asset_class: str
    min_size: Decimal | None
    max_size: Decimal | None
    lot_size: Decimal | None
    ko_level: Decimal | None
    strike: Decimal | None
    metadata_source: str | None
    canonical_underlying_id: str | None
    reference_epic: str | None
    binding_provenance: tuple[str, ...]
    currency: str | None
    bid: Decimal | None
    offer: Decimal | None
    market_status: str | None
    quote_source: str
    quote_received_at_utc: datetime
    availability: Availability
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.product_epic.strip() or not self.product_name.strip():
            raise ValueError("Paper ticket preparation requires exact product identity")
        _require_utc(self.quote_received_at_utc)
        if self.availability is Availability.READY:
            if (
                self.canonical_underlying_id is None
                or self.reference_epic is None
                or self.currency is None
                or self.bid is None
                or self.offer is None
            ):
                raise ValueError("ready Paper ticket preparation requires binding and quote")


def build_paper_ticket_preparation(
    *,
    product: ProductRowVM,
    binding: IGProductMarketBinding | None,
    evaluated_at_utc: datetime,
) -> PaperTicketPreparationVM:
    _require_utc(evaluated_at_utc)
    reasons: list[str] = []
    if binding is None:
        reasons.append("EXACT_PRODUCT_BINDING_REQUIRED")
    if product.product_type == "unknown":
        reasons.append("PRODUCT_TYPE_UNKNOWN")
    if not product.currency:
        reasons.append("PRODUCT_CURRENCY_UNAVAILABLE")
    if product.bid is None or product.offer is None:
        reasons.append("BID_OFFER_UNAVAILABLE")
    elif product.bid <= 0 or product.offer <= 0 or product.offer < product.bid:
        reasons.append("BID_OFFER_INVALID")
    if (product.status or "").upper() != "TRADEABLE":
        reasons.append("MARKET_NOT_CONFIRMED_TRADEABLE")
    age_seconds = (evaluated_at_utc - product.provenance.received_at_utc).total_seconds()
    if product.provenance.source != "ig-lightstreamer":
        reasons.append("LIVE_QUOTE_REQUIRED")
    elif not 0 <= age_seconds <= QUOTE_FRESHNESS_SECONDS:
        reasons.append("LIVE_QUOTE_STALE")
    if "BROKER_DELAYED" in product.provenance.reason_codes:
        reasons.append("BROKER_DELAYED")

    if not reasons:
        availability = Availability.READY
    elif binding is None or product.product_type == "unknown":
        availability = Availability.NOT_APPLICABLE
    elif "LIVE_QUOTE_STALE" in reasons or "BROKER_DELAYED" in reasons:
        availability = Availability.STALE
    else:
        availability = Availability.UNAVAILABLE
    return PaperTicketPreparationVM(
        product_epic=product.epic,
        product_name=product.name,
        product_type=product.product_type,
        product_direction=product.direction,
        asset_class=product.asset_class,
        min_size=product.min_size,
        max_size=product.max_size,
        lot_size=product.lot_size,
        ko_level=product.ko_level,
        strike=product.strike,
        metadata_source=product.metadata_source,
        canonical_underlying_id=(
            binding.canonical_underlying_id.value if binding is not None else None
        ),
        reference_epic=binding.reference_epic if binding is not None else None,
        binding_provenance=binding.provenance if binding is not None else (),
        currency=product.currency,
        bid=product.bid,
        offer=product.offer,
        market_status=product.status,
        quote_source=product.provenance.source,
        quote_received_at_utc=product.provenance.received_at_utc,
        availability=availability,
        reason_codes=tuple(reasons),
    )


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("Paper ticket preparation timestamp must use UTC")
