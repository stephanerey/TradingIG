"""Read-only product discovery service for IG market metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from trading_ig_assistant.domain.instruments import MarketDetails, MarketNavigation, MarketSummary
from trading_ig_assistant.domain.products import ProductDirection, ProductType, TradableProduct
from trading_ig_assistant.utils.redaction import REDACTED, is_secret_key, redact_mapping

DEFAULT_WATCHLIST_SEARCH_TERMS = ["US Tech 100", "France 40", "Germany 40", "Gold"]


class ProductDiscoveryAdapter(Protocol):
    def search_markets(self, query: str) -> list[MarketSummary]:
        """Search broker markets."""

    def get_market_details(self, epic: str) -> MarketDetails:
        """Fetch broker market details."""

    def get_market_navigation(self, node_id: str | None = None) -> MarketNavigation:
        """Browse broker market navigation."""


@dataclass(frozen=True)
class ProductDiscoveryError:
    epic: str | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"epic": self.epic, "message": self.message}


@dataclass(frozen=True)
class ProductDiscoveryResult:
    search_term: str
    candidates_count: int
    products: list[TradableProduct] = field(default_factory=list)
    errors: list[ProductDiscoveryError] = field(default_factory=list)

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "search_term": self.search_term,
            "candidates_count": self.candidates_count,
            "products": [sanitize_payload(product.to_dict()) for product in self.products],
            "errors": [error.to_dict() for error in self.errors],
        }


class ProductDiscoveryService:
    def __init__(self, adapter: ProductDiscoveryAdapter) -> None:
        self._adapter = adapter

    def discover_products(self, search_term: str) -> ProductDiscoveryResult:
        errors: list[ProductDiscoveryError] = []
        products: list[TradableProduct] = []
        try:
            summaries = self._adapter.search_markets(search_term)
        except Exception as exc:
            return ProductDiscoveryResult(
                search_term=search_term,
                candidates_count=0,
                errors=[ProductDiscoveryError(epic=None, message=str(exc))],
            )

        for summary in summaries:
            try:
                details = self._adapter.get_market_details(summary.epic)
                products.append(self.classify_product(summary, details))
            except Exception as exc:
                errors.append(ProductDiscoveryError(epic=summary.epic, message=str(exc)))

        return ProductDiscoveryResult(
            search_term=search_term,
            candidates_count=len(summaries),
            products=products,
            errors=errors,
        )

    def discover_watchlist_products(
        self,
        search_terms: list[str] | None = None,
    ) -> list[ProductDiscoveryResult]:
        terms = search_terms or DEFAULT_WATCHLIST_SEARCH_TERMS
        return [self.discover_products(search_term) for search_term in terms]

    def discover_all_products(self, *, max_nodes: int = 1000) -> ProductDiscoveryResult:
        errors: list[ProductDiscoveryError] = []
        products: list[TradableProduct] = []
        summaries_by_epic: dict[str, MarketSummary] = {}
        pending_node_ids: list[str | None] = [None]
        visited_node_ids: set[str] = set()

        while pending_node_ids and len(visited_node_ids) < max_nodes:
            node_id = pending_node_ids.pop(0)
            if node_id is not None:
                if node_id in visited_node_ids:
                    continue
                visited_node_ids.add(node_id)
            try:
                navigation = self._adapter.get_market_navigation(node_id)
            except Exception as exc:
                errors.append(ProductDiscoveryError(epic=node_id, message=str(exc)))
                continue

            pending_node_ids.extend(node.node_id for node in navigation.nodes if node.node_id)
            for summary in navigation.markets:
                if summary.epic:
                    summaries_by_epic.setdefault(summary.epic, summary)

        for summary in summaries_by_epic.values():
            try:
                details = self._adapter.get_market_details(summary.epic)
                products.append(self.classify_product(summary, details))
            except Exception as exc:
                errors.append(ProductDiscoveryError(epic=summary.epic, message=str(exc)))

        return ProductDiscoveryResult(
            search_term="market-navigation",
            candidates_count=len(summaries_by_epic),
            products=products,
            errors=errors,
        )

    def classify_product(
        self,
        summary: MarketSummary,
        details: MarketDetails | None,
    ) -> TradableProduct:
        raw_payload = sanitize_payload(
            {"summary": summary.raw, "details": details.raw if details else {}}
        )
        text = _flatten_text(
            [
                summary.epic,
                summary.instrument_name,
                summary.instrument_type,
                summary.expiry,
                summary.market_status,
                summary.raw,
                details.instrument_name if details else "",
                details.raw if details else {},
            ]
        )
        product_type = _classify_product_type(text, summary)
        direction = _classify_direction(text, product_type)
        details_raw = details.raw if details else {}

        return TradableProduct(
            epic=summary.epic or (details.epic if details else ""),
            name=summary.instrument_name or (details.instrument_name if details else ""),
            product_type=product_type,
            direction=direction,
            instrument_type=summary.instrument_type
            or _first_string(details_raw, ["instrumentType"]),
            expiry=summary.expiry or _first_string(details_raw, ["expiry"]),
            currency=_first_string(
                {"summary": summary.raw, "details": details_raw},
                ["currency", "currencies", "baseCurrency", "quoteCurrency"],
            ),
            min_size=_first_float(
                {"summary": summary.raw, "details": details_raw},
                ["minDealSize", "minimumDealSize", "minSize", "min_size"],
            ),
            max_size=_first_float(
                {"summary": summary.raw, "details": details_raw},
                ["maxDealSize", "maximumDealSize", "maxSize", "max_size"],
            ),
            lot_size=_first_float(
                {"summary": summary.raw, "details": details_raw},
                ["lotSize", "lot_size", "contractSize", "unit"],
            ),
            status=summary.market_status or _first_string(details_raw, ["marketStatus", "status"]),
            ko_level=_first_float(
                {"summary": summary.raw, "details": details_raw},
                ["koLevel", "knockoutLevel", "knockOutLevel", "barrierLevel", "barrier"],
            ),
            strike=_first_float(
                {"summary": summary.raw, "details": details_raw},
                ["strike", "strikePrice", "exercisePrice"],
            ),
            raw=raw_payload,
        )


def sanitize_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        clean: dict[str, Any] = {}
        for key, value in payload.items():
            key_text = str(key)
            if is_secret_key(key_text):
                clean[key_text] = REDACTED
            elif key_text.lower() in {"accountid", "account_id"}:
                clean[key_text] = _mask_identifier(str(value))
            else:
                clean[key_text] = sanitize_payload(value)
        return redact_mapping(clean)
    if isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    if isinstance(payload, tuple):
        return [sanitize_payload(item) for item in payload]
    return payload


def discovery_results_to_report(results: list[ProductDiscoveryResult]) -> dict[str, Any]:
    return {
        "schema": "trading_ig_assistant.product_discovery.v1",
        "results": [result.to_sanitized_dict() for result in results],
    }


def write_discovery_report(results: list[ProductDiscoveryResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = discovery_results_to_report(results)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _mask_identifier(value: str) -> str:
    if len(value) <= 4:
        return REDACTED
    return f"{value[:2]}...{value[-2:]}"


def _classify_product_type(text: str, summary: MarketSummary) -> ProductType:
    if any(token in text for token in ("barrier", "knockout", "knock-out", "knock out")):
        return ProductType.BARRIER
    if any(token in text for token in (" option", "option ", "vanilla", " call ", " put ")):
        return ProductType.OPTION
    instrument_type = (summary.instrument_type or "").upper()
    expiry = (summary.expiry or "").upper()
    if expiry in {"DFB", "-"} or "CASH" in text:
        return ProductType.CASH_OR_DFB
    if instrument_type in {"INDICES", "CURRENCIES", "COMMODITIES", "SHARES", "RATES"}:
        return ProductType.CASH_OR_DFB
    return ProductType.UNKNOWN


def _classify_direction(text: str, product_type: ProductType) -> ProductDirection:
    padded = f" {text} "
    if product_type == ProductType.OPTION:
        if any(token in padded for token in (" call ", " calls ")):
            return ProductDirection.CALL
        if any(token in padded for token in (" put ", " puts ")):
            return ProductDirection.PUT
    if product_type == ProductType.BARRIER:
        if any(token in padded for token in (" buy ", " bull ", " long ", " up ")):
            return ProductDirection.BUY
        if any(token in padded for token in (" sell ", " bear ", " short ", " down ")):
            return ProductDirection.SELL
    return ProductDirection.UNKNOWN


def _flatten_text(values: list[Any]) -> str:
    chunks: list[str] = []
    for value in values:
        if isinstance(value, dict):
            chunks.extend(str(item) for pair in value.items() for item in pair)
        elif isinstance(value, list):
            chunks.extend(str(item) for item in value)
        elif value is not None:
            chunks.append(str(value))
    return f" {' '.join(chunks).lower()} "


def _first_string(payload: Any, keys: list[str]) -> str | None:
    value = _first_value(payload, keys)
    if value is None:
        return None
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _first_float(payload: Any, keys: list[str]) -> float | None:
    value = _first_value(payload, keys)
    if isinstance(value, dict):
        value = value.get("value")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_value(payload: Any, keys: list[str]) -> Any:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key) in keys:
                return value
            nested = _first_value(value, keys)
            if nested is not None:
                return nested
    if isinstance(payload, list):
        for item in payload:
            nested = _first_value(item, keys)
            if nested is not None:
                return nested
    return None
