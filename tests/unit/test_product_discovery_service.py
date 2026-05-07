import json

from trading_ig_assistant.domain.instruments import (
    MarketDetails,
    MarketNavigation,
    MarketNavigationNode,
    MarketSummary,
)
from trading_ig_assistant.domain.products import ProductDirection, ProductType
from trading_ig_assistant.services.product_discovery_service import (
    ProductDiscoveryService,
    write_discovery_report,
)


class FakeDiscoveryAdapter:
    def __init__(self) -> None:
        self.detail_calls: list[str] = []

    def search_markets(self, query: str) -> list[MarketSummary]:
        if query == "US Tech 100":
            return [
                MarketSummary(
                    epic="BARRIER.EPIC",
                    instrument_name="US Tech 100 Barrier Long",
                    instrument_type="INDICES",
                    expiry="DFB",
                    market_status="TRADEABLE",
                    raw={"epic": "BARRIER.EPIC", "accountId": "ABCDEF123456"},
                ),
                MarketSummary(
                    epic="OPTION.EPIC",
                    instrument_name="US Tech 100 Call Option",
                    instrument_type="OPTION",
                    expiry="JUN-26",
                    market_status="TRADEABLE",
                    raw={"epic": "OPTION.EPIC"},
                ),
                MarketSummary(
                    epic="BROKEN.EPIC",
                    instrument_name="Broken candidate",
                    raw={},
                ),
            ]
        return []

    def get_market_details(self, epic: str) -> MarketDetails:
        self.detail_calls.append(epic)
        if epic == "BROKEN.EPIC":
            raise RuntimeError("details unavailable")
        if epic == "BARRIER.EPIC":
            return MarketDetails(
                epic=epic,
                instrument_name="US Tech 100 Barrier Long",
                raw={
                    "instrument": {
                        "name": "US Tech 100 Barrier Long",
                        "currency": "EUR",
                        "knockoutLevel": {"value": "18000"},
                    },
                    "dealingRules": {"minDealSize": {"value": "0.5"}},
                    "secretToken": "fake-token",
                },
            )
        return MarketDetails(
            epic=epic,
            instrument_name="US Tech 100 Call Option",
            raw={
                "instrument": {
                    "name": "US Tech 100 Call Option",
                    "currency": "EUR",
                    "strikePrice": "19000",
                },
                "dealingRules": {"minDealSize": {"value": "1"}},
            },
        )

    def get_market_navigation(self, node_id: str | None = None) -> MarketNavigation:
        if node_id is None:
            return MarketNavigation(
                nodes=[MarketNavigationNode(node_id="indices", name="Indices")],
                markets=[],
            )
        if node_id == "indices":
            return MarketNavigation(
                nodes=[],
                markets=[
                    MarketSummary(
                        epic="BARRIER.EPIC",
                        instrument_name="US Tech 100 Barrier Long",
                        instrument_type="INDICES",
                        raw={},
                    ),
                    MarketSummary(
                        epic="OPTION.EPIC",
                        instrument_name="US Tech 100 Call Option",
                        instrument_type="OPTION",
                        raw={},
                    ),
                ],
            )
        return MarketNavigation()


class EmptyNavigationAdapter(FakeDiscoveryAdapter):
    def get_market_navigation(self, node_id: str | None = None) -> MarketNavigation:
        raise RuntimeError("navigation unavailable")


def test_classification_heuristics_identify_barrier_and_option() -> None:
    service = ProductDiscoveryService(FakeDiscoveryAdapter())

    result = service.discover_products("US Tech 100")

    assert result.candidates_count == 3
    assert len(result.products) == 2
    assert len(result.errors) == 1

    barrier = result.products[0]
    assert barrier.product_type == ProductType.BARRIER
    assert barrier.direction == ProductDirection.BUY
    assert barrier.ko_level == 18000.0
    assert barrier.min_size == 0.5

    option = result.products[1]
    assert option.product_type == ProductType.OPTION
    assert option.direction == ProductDirection.CALL
    assert option.strike == 19000.0


def test_sanitized_report_excludes_sensitive_values(tmp_path) -> None:
    service = ProductDiscoveryService(FakeDiscoveryAdapter())
    result = service.discover_products("US Tech 100")
    output_path = tmp_path / "product_discovery.json"

    write_discovery_report([result], output_path)

    report_text = output_path.read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert "fake-token" not in report_text
    assert "ABCDEF123456" not in report_text
    assert report["schema"] == "trading_ig_assistant.product_discovery.v1"
    assert report["results"][0]["products"][0]["raw"]["summary"]["accountId"] == "AB...56"


def test_discover_all_products_uses_market_navigation() -> None:
    adapter = FakeDiscoveryAdapter()
    service = ProductDiscoveryService(adapter)

    result = service.discover_all_products()

    assert result.search_term == "market-navigation"
    assert result.candidates_count == 2
    assert {product.epic for product in result.products} == {"BARRIER.EPIC", "OPTION.EPIC"}
    assert adapter.detail_calls == []


def test_discover_all_products_falls_back_to_search_when_navigation_unavailable() -> None:
    adapter = EmptyNavigationAdapter()
    service = ProductDiscoveryService(adapter)

    result = service.discover_all_products()

    assert result.search_term == "market-navigation+search-fallback"
    assert result.candidates_count == 3
    assert {product.epic for product in result.products} == {
        "BARRIER.EPIC",
        "OPTION.EPIC",
        "BROKEN.EPIC",
    }
    assert adapter.detail_calls == []
    assert len(result.errors) == 1
