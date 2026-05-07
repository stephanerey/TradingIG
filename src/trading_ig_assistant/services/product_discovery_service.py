"""Read-only product discovery service for IG market metadata."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from trading_ig_assistant.domain.instruments import (
    MarketCategory,
    MarketDetails,
    MarketNavigation,
    MarketSummary,
)
from trading_ig_assistant.domain.products import (
    AssetClass,
    ProductDirection,
    ProductType,
    TradableProduct,
)
from trading_ig_assistant.utils.redaction import REDACTED, is_secret_key, redact_mapping

DEFAULT_WATCHLIST_SEARCH_TERMS = ["US Tech 100", "France 40", "Germany 40", "Gold"]
DEFAULT_DISCOVERY_FALLBACK_SEARCH_TERMS = [
    "US Tech 100",
    "US 500",
    "Wall Street",
    "Germany 40",
    "France 40",
    "FTSE 100",
    "Japan 225",
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "EUR/GBP",
    "Gold",
    "Silver",
    "Crude",
    "Oil",
    "Bitcoin",
    "Ethereum",
    "Carrefour",
    "Verallia",
    "Capgemini",
    "Cap Gemini",
    "L'Oreal",
    "LVMH",
    "Air Liquide",
    "TotalEnergies",
    "Sanofi",
    "Schneider",
    "Dassault",
    "EssilorLuxottica",
    "Edenred",
    "Eramet",
    "Eutelsat",
    "Forvia",
    "Nexans",
    "Orange",
    "Renault",
    "Stellantis",
    "Thales",
    "Vinci",
    "Bouygues",
    "AXA",
    "BNP Paribas",
    "Credit Agricole",
    "Societe Generale",
    "Hermes",
    "Kering",
    "Publicis",
    "Saint Gobain",
    "Pernod Ricard",
    "Danone",
    "Michelin",
    "Safran",
    "Engie",
    "Veolia",
    "Vivendi",
    "Worldline",
    "Alstom",
    "Teleperformance",
    "Accor",
    "Sodexo",
    "Ubisoft",
    "Ipsen",
    "Arkema",
    "Bureau Veritas",
    "Eiffage",
    "Eurofins",
    "Legrand",
    "Sartorius",
    "Sopra Steria",
    "Valeo",
    "AstraZeneca",
    "Barclays",
    "BP",
    "HSBC",
    "Rio Tinto",
    "Shell",
    "Unilever",
    "Vodafone",
    "Apple",
    "Microsoft",
    "Nvidia",
    "Tesla",
    "Amazon",
    "Meta",
    "Alphabet",
    "Netflix",
    "Wall Street",
    "Barrier",
    "Option",
]
LOGGER = logging.getLogger(__name__)


class ProductDiscoveryAdapter(Protocol):
    def search_markets(self, query: str) -> list[MarketSummary]:
        """Search broker markets."""

    def get_market_details(self, epic: str) -> MarketDetails:
        """Fetch broker market details."""

    def get_categories(self) -> list[MarketCategory]:
        """Fetch market categories enabled for the active account."""

    def get_category_instruments(self, category_id: str) -> list[MarketSummary]:
        """Fetch instruments for an enabled category."""

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
        LOGGER.debug("Product discovery search start search_term=%r", search_term)
        errors: list[ProductDiscoveryError] = []
        products: list[TradableProduct] = []
        try:
            summaries = self._adapter.search_markets(search_term)
        except Exception as exc:
            LOGGER.debug(
                "Product discovery search failed search_term=%r error=%s",
                search_term,
                exc,
            )
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
                LOGGER.debug(
                    "Product discovery details failed search_term=%r epic=%s error=%s",
                    search_term,
                    summary.epic,
                    exc,
                )
                errors.append(ProductDiscoveryError(epic=summary.epic, message=str(exc)))

        LOGGER.debug(
            "Product discovery search complete search_term=%r candidates=%s products=%s errors=%s",
            search_term,
            len(summaries),
            len(products),
            len(errors),
        )
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

    def discover_all_products(
        self,
        *,
        max_nodes: int = 1000,
        max_details: int = 0,
    ) -> ProductDiscoveryResult:
        """Discover products through IG market navigation.

        By default this intentionally does not fetch details for every EPIC. A full detail scan
        creates a large burst of `/markets/{epic}` calls and IG may reject the session token.
        """

        LOGGER.debug(
            "Product discovery all start max_nodes=%s max_details=%s",
            max_nodes,
            max_details,
        )
        errors: list[ProductDiscoveryError] = []
        products: list[TradableProduct] = []
        summaries_by_epic: dict[str, MarketSummary] = {}
        category_errors = self._discover_category_summaries(summaries_by_epic)
        errors.extend(category_errors)
        category_product_count = len(summaries_by_epic)

        navigation_was_used = False
        if not summaries_by_epic:
            navigation_was_used = True
            self._discover_navigation_summaries(summaries_by_epic, errors, max_nodes=max_nodes)

        fallback_was_used = False
        if not summaries_by_epic:
            fallback_was_used = True
            LOGGER.debug(
                "Product discovery navigation empty; starting search fallback terms=%s",
                DEFAULT_DISCOVERY_FALLBACK_SEARCH_TERMS,
            )
            summaries_by_epic.update(
                self._fallback_search_summaries(DEFAULT_DISCOVERY_FALLBACK_SEARCH_TERMS, errors)
            )

        for index, summary in enumerate(summaries_by_epic.values()):
            details = None
            if max_details > 0 and index < max_details:
                try:
                    details = self._adapter.get_market_details(summary.epic)
                except Exception as exc:
                    LOGGER.debug(
                        "Product discovery navigation details failed epic=%s error=%s",
                        summary.epic,
                        exc,
                    )
                    errors.append(ProductDiscoveryError(epic=summary.epic, message=str(exc)))
            products.append(self.classify_product(summary, details))

        LOGGER.debug(
            "Product discovery all complete candidates=%s products=%s errors=%s",
            len(summaries_by_epic),
            len(products),
            len(errors),
        )
        source_parts: list[str] = []
        if category_product_count:
            source_parts.append("categories")
        if navigation_was_used:
            source_parts.append("market-navigation")
        if fallback_was_used:
            source_parts.append("search-fallback")
        source = "+".join(source_parts) or "categories"
        return ProductDiscoveryResult(
            search_term=source,
            candidates_count=len(summaries_by_epic),
            products=products,
            errors=errors,
        )

    def _discover_category_summaries(
        self,
        summaries_by_epic: dict[str, MarketSummary],
    ) -> list[ProductDiscoveryError]:
        errors: list[ProductDiscoveryError] = []
        try:
            categories = self._adapter.get_categories()
        except Exception as exc:
            LOGGER.debug("Product discovery categories failed error=%s", exc)
            return [ProductDiscoveryError(epic=None, message=str(exc))]

        LOGGER.debug("Product discovery categories complete count=%s", len(categories))
        for category in categories:
            if not category.category_id:
                continue
            try:
                summaries = self._adapter.get_category_instruments(category.category_id)
            except Exception as exc:
                LOGGER.debug(
                    "Product discovery category instruments failed category=%s error=%s",
                    category.category_id,
                    exc,
                )
                errors.append(ProductDiscoveryError(epic=category.category_id, message=str(exc)))
                continue
            LOGGER.debug(
                "Product discovery category instruments complete category=%s name=%r count=%s",
                category.category_id,
                category.name,
                len(summaries),
            )
            for summary in summaries:
                if summary.epic:
                    summaries_by_epic.setdefault(summary.epic, summary)
        return errors

    def _discover_navigation_summaries(
        self,
        summaries_by_epic: dict[str, MarketSummary],
        errors: list[ProductDiscoveryError],
        *,
        max_nodes: int,
    ) -> None:
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
                LOGGER.debug(
                    "Product discovery navigation node failed node_id=%s error=%s",
                    node_id or "<root>",
                    exc,
                )
                errors.append(ProductDiscoveryError(epic=node_id, message=str(exc)))
                continue

            pending_node_ids.extend(node.node_id for node in navigation.nodes if node.node_id)
            for summary in navigation.markets:
                if summary.epic:
                    summaries_by_epic.setdefault(summary.epic, summary)
            LOGGER.debug(
                "Product discovery navigation node complete node_id=%s visited=%s pending=%s "
                "unique_markets=%s errors=%s",
                node_id or "<root>",
                len(visited_node_ids),
                len(pending_node_ids),
                len(summaries_by_epic),
                len(errors),
            )

    def _fallback_search_summaries(
        self,
        search_terms: list[str],
        errors: list[ProductDiscoveryError],
    ) -> dict[str, MarketSummary]:
        summaries_by_epic: dict[str, MarketSummary] = {}
        for search_term in search_terms:
            try:
                summaries = self._adapter.search_markets(search_term)
            except Exception as exc:
                LOGGER.debug(
                    "Product discovery fallback search failed search_term=%r error=%s",
                    search_term,
                    exc,
                )
                errors.append(ProductDiscoveryError(epic=None, message=str(exc)))
                continue
            LOGGER.debug(
                "Product discovery fallback search complete search_term=%r count=%s",
                search_term,
                len(summaries),
            )
            for summary in summaries:
                if summary.epic:
                    summaries_by_epic.setdefault(summary.epic, summary)
        LOGGER.debug(
            "Product discovery fallback complete unique_markets=%s errors=%s",
            len(summaries_by_epic),
            len(errors),
        )
        return summaries_by_epic

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
        asset_class = _classify_asset_class(text, summary)
        details_raw = details.raw if details else {}
        quote_payload = {"summary": summary.raw, "details": details_raw}

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
            asset_class=asset_class,
            bid=_first_float(quote_payload, ["bid", "bidPrice", "sell", "sellPrice"]),
            offer=_first_float(quote_payload, ["offer", "offerPrice", "ask", "buy", "buyPrice"]),
            net_change=_first_float(
                quote_payload,
                ["netChange", "change", "changeNet", "priceChange"],
            ),
            percent_change=_first_float(
                quote_payload,
                ["percentageChange", "percentChange", "changePct", "changePercent"],
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


def _classify_asset_class(text: str, summary: MarketSummary) -> AssetClass:
    instrument_type = (summary.instrument_type or "").upper()
    if instrument_type in {"CURRENCIES", "FOREX", "FX"}:
        return AssetClass.FOREX
    if instrument_type in {"COMMODITIES"}:
        return AssetClass.COMMODITIES
    if instrument_type in {"SHARES", "EQUITIES"}:
        return AssetClass.SHARES
    if instrument_type in {"INDICES", "BINARY"}:
        return AssetClass.INDICES
    if any(token in text for token in (" crypto", "bitcoin", "ethereum", "ether", "btc", "eth")):
        return AssetClass.CRYPTO
    if any(token in text for token in ("eur/usd", "gbp/usd", "usd/jpy", "eur/gbp", "forex")):
        return AssetClass.FOREX
    if any(token in text for token in ("gold", "silver", "oil", "crude", "copper", "commodity")):
        return AssetClass.COMMODITIES
    if any(token in text for token in ("share", " sa ", " plc ", " corp", " inc", "ltd")):
        return AssetClass.SHARES
    if any(token in text for token in ("index", "indice", "indices", "tech 100", "wall street")):
        return AssetClass.INDICES
    return AssetClass.OTHER


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
