import json

from trading_ig_assistant.domain.instruments import (
    MarketCategory,
    MarketDetails,
    MarketNavigation,
    MarketNavigationNode,
    MarketSummary,
)
from trading_ig_assistant.domain.products import ProductDirection, ProductType
from trading_ig_assistant.services.product_discovery_service import (
    CRYPTO_DISCOVERY_SEEDS,
    DEFAULT_DISCOVERY_FALLBACK_SEARCH_TERMS,
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
                    raw={
                        "epic": "BARRIER.EPIC",
                        "accountId": "ABCDEF123456",
                        "bid": 100.5,
                        "offer": 101.0,
                        "netChange": -1.5,
                        "percentageChange": -0.3,
                    },
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

    def get_categories(self) -> list[MarketCategory]:
        raise RuntimeError("categories unavailable")

    def get_category_instruments(self, category_id: str) -> list[MarketSummary]:
        raise RuntimeError(f"category {category_id} unavailable")

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


class CategoryDiscoveryAdapter(FakeDiscoveryAdapter):
    def get_categories(self) -> list[MarketCategory]:
        return [MarketCategory(category_id="shares", name="Shares")]

    def get_category_instruments(self, category_id: str) -> list[MarketSummary]:
        assert category_id == "shares"
        return [
            MarketSummary(
                epic="CARREFOUR.EPIC",
                instrument_name="Carrefour SA Barrier Call",
                instrument_type="SHARES",
                market_status="TRADEABLE",
                raw={"bid": 1708.5, "offer": 1709.5},
            )
        ]


class AllowanceExceededNavigationAdapter(FakeDiscoveryAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.search_calls: list[str] = []

    def get_market_navigation(self, node_id: str | None = None) -> MarketNavigation:
        raise RuntimeError(
            "IG REST request failed with HTTP 403: {'errorCode': "
            "'error.public-api.exceeded-api-key-allowance'}"
        )

    def search_markets(self, query: str) -> list[MarketSummary]:
        self.search_calls.append(query)
        return super().search_markets(query)


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
    assert barrier.asset_class.value == "indices"
    assert barrier.bid == 100.5
    assert barrier.offer == 101.0
    assert barrier.net_change == -1.5
    assert barrier.percent_change == -0.3

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


def test_discover_all_products_prefers_enabled_categories() -> None:
    adapter = CategoryDiscoveryAdapter()
    service = ProductDiscoveryService(adapter)

    result = service.discover_all_products()

    assert result.search_term == "categories"
    assert result.candidates_count == 1
    assert result.products[0].epic == "CARREFOUR.EPIC"
    assert result.products[0].asset_class.value == "shares"
    assert result.products[0].bid == 1708.5
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
    assert len(result.errors) == 2


def test_discover_all_products_stops_after_allowance_exceeded() -> None:
    adapter = AllowanceExceededNavigationAdapter()
    service = ProductDiscoveryService(adapter)

    result = service.discover_all_products()

    assert result.search_term == "market-navigation"
    assert result.candidates_count == 0
    assert len(result.errors) == 2
    assert adapter.search_calls == []


def test_crypto_discovery_seeds_cover_ig_crypto_barrier_tab() -> None:
    expected = {
        "Bitcoin",
        "Ether",
        "Solana",
        "Chainlink",
        "Polkadot",
        "Uniswap",
        "Avalanche",
        "Dogecoin",
        "Litecoin",
        "Ripple",
        "Stellar",
    }

    assert expected.issubset(set(CRYPTO_DISCOVERY_SEEDS))
    assert len(DEFAULT_DISCOVERY_FALLBACK_SEARCH_TERMS) == len(
        set(DEFAULT_DISCOVERY_FALLBACK_SEARCH_TERMS)
    )
