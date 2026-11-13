"""Immutable product-catalogue projection for GUI V2."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal

from trading_ig_assistant.app.projections.common import Availability, DataProvenance
from trading_ig_assistant.domain.market_data import Quote
from trading_ig_assistant.domain.products import TradableProduct


@dataclass(frozen=True)
class ProductRowVM:
    epic: str
    name: str
    product_type: str
    direction: str
    asset_class: str
    status: str | None
    currency: str | None
    bid: Decimal | None
    offer: Decimal | None
    net_change: Decimal | None
    percent_change: Decimal | None
    provenance: DataProvenance
    min_size: Decimal | None = None
    max_size: Decimal | None = None
    lot_size: Decimal | None = None
    ko_level: Decimal | None = None
    strike: Decimal | None = None
    metadata_source: str | None = None


@dataclass(frozen=True)
class CatalogueVM:
    generation_id: int
    query: str | None
    rows: tuple[ProductRowVM, ...]
    availability: Availability
    generated_at_utc: datetime
    error_count: int = 0
    kind: str = "search"

    def __post_init__(self) -> None:
        if self.generation_id < 0:
            raise ValueError("catalogue generation must be non-negative")
        if self.generated_at_utc.tzinfo is None or (
            self.generated_at_utc.utcoffset() != UTC.utcoffset(self.generated_at_utc)
        ):
            raise ValueError("catalogue timestamp must use UTC")


def build_catalogue_projection(
    *,
    generation_id: int,
    query: str,
    products: tuple[TradableProduct, ...],
    generated_at_utc: datetime,
    error_count: int = 0,
    kind: str = "search",
    source: str = "ig-rest-search-markets",
) -> CatalogueVM:
    scope = f"ig-search:{query}"
    return CatalogueVM(
        generation_id=generation_id,
        query=query,
        rows=tuple(
            ProductRowVM(
                epic=product.epic,
                name=product.name or product.epic,
                product_type=product.product_type.value,
                direction=product.direction.value,
                asset_class=product.asset_class.value,
                status=product.status,
                currency=product.currency,
                bid=_decimal(product.bid),
                offer=_decimal(product.offer),
                net_change=_decimal(product.net_change),
                percent_change=_decimal(product.percent_change),
                provenance=DataProvenance(
                    source=source,
                    observed_at_utc=None,
                    received_at_utc=generated_at_utc,
                    scope=scope,
                    availability=Availability.READY,
                    reason_codes=(
                        "CACHED_INVENTORY" if source == "local-discovery-cache" else "SUMMARY_ONLY",
                    ),
                ),
                min_size=_decimal(product.min_size),
                max_size=_decimal(product.max_size),
                lot_size=_decimal(product.lot_size),
                ko_level=_decimal(product.ko_level),
                strike=_decimal(product.strike),
                metadata_source=source,
            )
            for product in products
        ),
        availability=Availability.READY,
        generated_at_utc=generated_at_utc,
        error_count=error_count,
        kind=kind,
    )


def empty_catalogue_projection(generation_id: int, now: datetime) -> CatalogueVM:
    return CatalogueVM(
        generation_id=generation_id,
        query=None,
        rows=(),
        availability=Availability.UNAVAILABLE,
        generated_at_utc=now,
        kind="empty",
    )


def merge_catalogue_snapshots(
    current: CatalogueVM,
    additions: CatalogueVM,
) -> CatalogueVM:
    """Append newly discovered products without replacing live rows already observed."""

    rows = list(current.rows)
    known_epics = {row.epic for row in rows}
    rows.extend(row for row in additions.rows if row.epic not in known_epics)
    return replace(
        current,
        rows=tuple(rows),
        availability=Availability.READY,
        error_count=current.error_count + additions.error_count,
        kind="inventory" if current.rows else additions.kind,
    )


def merge_catalogue_product_details(
    snapshot: CatalogueVM,
    *,
    product: TradableProduct,
) -> CatalogueVM | None:
    """Merge one explicit REST details lookup without replacing live quote evidence."""

    rows: list[ProductRowVM] = []
    matched = False
    for row in snapshot.rows:
        if row.epic != product.epic:
            rows.append(row)
            continue
        matched = True
        rows.append(
            replace(
                row,
                name=product.name or row.name,
                product_type=(
                    row.product_type
                    if row.product_type != "unknown"
                    else product.product_type.value
                ),
                direction=(
                    row.direction if row.direction != "unknown" else product.direction.value
                ),
                asset_class=(
                    row.asset_class if row.asset_class != "other" else product.asset_class.value
                ),
                status=row.status or product.status,
                currency=product.currency or row.currency,
                min_size=_decimal(product.min_size),
                max_size=_decimal(product.max_size),
                lot_size=_decimal(product.lot_size),
                ko_level=_decimal(product.ko_level),
                strike=_decimal(product.strike),
                metadata_source="ig-rest-market-details",
            )
        )
    return replace(snapshot, rows=tuple(rows)) if matched else None


def mark_stream_rows_stale(
    snapshot: CatalogueVM,
    *,
    epics: frozenset[str],
    received_at_utc: datetime,
    reason_code: str,
) -> CatalogueVM | None:
    rows: list[ProductRowVM] = []
    changed = False
    for row in snapshot.rows:
        if row.epic not in epics or row.provenance.source != "ig-lightstreamer":
            rows.append(row)
            continue
        changed = True
        rows.append(
            replace(
                row,
                provenance=replace(
                    row.provenance,
                    received_at_utc=received_at_utc,
                    availability=Availability.STALE,
                    reason_codes=tuple(dict.fromkeys((*row.provenance.reason_codes, reason_code))),
                ),
            )
        )
    return replace(snapshot, rows=tuple(rows)) if changed else None


def merge_live_quote(
    snapshot: CatalogueVM,
    *,
    quote: Quote,
    received_at_utc: datetime,
) -> CatalogueVM | None:
    """Merge one observed Lightstreamer quote into its catalogue row.

    The function never invents a row: an explicit REST catalogue search must have
    exposed the EPIC before it can receive a live update in GUI V2.
    """

    observed_at = _quote_observed_at_utc(quote.timestamp_ms)
    reason_codes = ("LIVE_QUOTE",)
    availability = Availability.STALE if quote.delayed is True else Availability.READY
    if quote.delayed is True:
        reason_codes += ("BROKER_DELAYED",)
    rows: list[ProductRowVM] = []
    matched = False
    for row in snapshot.rows:
        if row.epic != quote.epic:
            rows.append(row)
            continue
        matched = True
        rows.append(
            replace(
                row,
                bid=_decimal(quote.bid) if quote.bid is not None else row.bid,
                offer=_decimal(quote.offer) if quote.offer is not None else row.offer,
                net_change=(
                    _decimal(quote.net_change)
                    if quote.net_change is not None
                    else row.net_change
                ),
                percent_change=(
                    _decimal(quote.percent_change)
                    if quote.percent_change is not None
                    else row.percent_change
                ),
                status=quote.market_state or row.status,
                provenance=DataProvenance(
                    source="ig-lightstreamer",
                    observed_at_utc=observed_at,
                    received_at_utc=received_at_utc,
                    scope=f"ig-stream:{quote.epic}",
                    availability=availability,
                    reason_codes=reason_codes,
                ),
            )
        )
    if not matched:
        return None
    return replace(
        snapshot,
        rows=tuple(rows),
        availability=availability,
    )


def _decimal(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _quote_observed_at_utc(timestamp_ms: int | None) -> datetime | None:
    if timestamp_ms is None or timestamp_ms < 100_000_000_000:
        return None
    try:
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
    except (OSError, OverflowError, ValueError):
        return None
