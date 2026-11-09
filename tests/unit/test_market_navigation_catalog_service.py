import pytest

from trading_ig_assistant.domain.instruments import (
    MarketCategory,
    MarketNavigation,
    MarketNavigationNode,
    MarketSummary,
)
from trading_ig_assistant.domain.market_navigation import (
    INITIAL_IG_REFERENCE_EPICS,
    IGMarketFamilyDefinition,
    IGProductMarketBinding,
    IGReferenceMarketDefinition,
    initial_ig_reference_epics,
)
from trading_ig_assistant.domain.markets import CanonicalUnderlyingId
from trading_ig_assistant.services.market_navigation_catalog_service import (
    IGMarketFamilyRegistry,
    IGProductMarketBindingRegistry,
    IGReferenceMarketRegistry,
    LazyIGCategoryCatalog,
    LazyMarketNavigationCatalog,
    MarketNavigationCatalogError,
)


class SyntheticIGNavigationAdapter:
    def get_market_navigation(self, node_id: str | None = None) -> MarketNavigation:
        pages = {
            None: MarketNavigation(
                nodes=[MarketNavigationNode("indices", "Indices")],
            ),
            "indices": MarketNavigation(
                nodes=[
                    MarketNavigationNode("us-tech-100", "US Tech 100"),
                    MarketNavigationNode("france-40", "France 40"),
                ],
            ),
            "us-tech-100": MarketNavigation(
                markets=[
                    MarketSummary("IX.D.NASDAQ.IFD.IP", "US Tech 100 Cash"),
                    MarketSummary("IX.D.NASDAQ.OPTCALL2.IP", "US Tech 100 Barrier Call"),
                ],
            ),
            "france-40": MarketNavigation(
                markets=[MarketSummary("IX.D.CAC.IFD.IP", "France 40 Cash")],
            ),
        }
        return pages[node_id]


class SyntheticIGCategoryAdapter:
    def get_categories(self) -> list[MarketCategory]:
        return [
            MarketCategory("INDICES", "INDICES", raw={"code": "INDICES"}),
            MarketCategory("COMMODITIES", "COMMODITIES", raw={"code": "COMMODITIES"}),
        ]

    def get_category_instruments(self, category_id: str) -> list[MarketSummary]:
        if category_id == "INDICES":
            return [
                MarketSummary(
                    "IX.D.NASDAQ.IFD.IP",
                    "US Tech 100 Cash",
                    raw={"underlyingName": "US Tech 100"},
                ),
                MarketSummary(
                    "IX.D.CAC.IMF.IP",
                    "France 40 Cash",
                    raw={"underlyingName": "France 40"},
                ),
            ]
        return [
            MarketSummary(
                "CS.D.CFEGOLD.CEF.IP",
                "Spot Gold",
                raw={"underlyingName": "Spot Gold"},
            )
        ]


def _us_tech_page():
    catalog = LazyMarketNavigationCatalog(SyntheticIGNavigationAdapter())
    catalog.browse_root()
    catalog.browse_node("indices")
    return catalog.browse_node("us-tech-100")


def test_lazy_catalog_retains_exact_ig_breadcrumb_without_traversing_every_node() -> None:
    catalog = LazyMarketNavigationCatalog(SyntheticIGNavigationAdapter())

    root = catalog.browse_root()
    indices = catalog.browse_node("indices")
    us_tech = catalog.browse_node("us-tech-100")

    assert root.breadcrumb == ()
    assert [node.name for node in indices.breadcrumb] == ["Indices"]
    assert [node.name for node in us_tech.breadcrumb] == ["Indices", "US Tech 100"]
    assert [market.epic for market in us_tech.markets] == [
        "IX.D.NASDAQ.IFD.IP",
        "IX.D.NASDAQ.OPTCALL2.IP",
    ]


def test_product_resolves_from_explicit_family_node_to_reference_epic() -> None:
    registry = IGMarketFamilyRegistry(
        (
            IGMarketFamilyDefinition(
                canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
                family_node_id="us-tech-100",
                reference_epic="IX.D.NASDAQ.IFD.IP",
            ),
        )
    )

    resolved = registry.resolve(
        page=_us_tech_page(),
        product_epic="IX.D.NASDAQ.OPTCALL2.IP",
    )

    assert resolved.canonical_underlying_id is CanonicalUnderlyingId.US_TECH_100
    assert resolved.reference_epic == "IX.D.NASDAQ.IFD.IP"
    assert resolved.product_epic == "IX.D.NASDAQ.OPTCALL2.IP"
    assert resolved.provenance[0] == "ig:market-navigation"


def test_unknown_node_product_or_family_fails_closed() -> None:
    catalog = LazyMarketNavigationCatalog(SyntheticIGNavigationAdapter())

    with pytest.raises(MarketNavigationCatalogError, match="first be discovered"):
        catalog.browse_node("us-tech-100")

    page = _us_tech_page()
    empty_registry = IGMarketFamilyRegistry(())
    with pytest.raises(MarketNavigationCatalogError, match="not present"):
        empty_registry.resolve(page=page, product_epic="UNKNOWN.EPIC")
    with pytest.raises(MarketNavigationCatalogError, match="no explicit"):
        empty_registry.resolve(page=page, product_epic="IX.D.NASDAQ.OPTCALL2.IP")


def test_ambiguous_parent_and_child_family_definitions_fail_closed() -> None:
    registry = IGMarketFamilyRegistry(
        (
            IGMarketFamilyDefinition(
                CanonicalUnderlyingId.US_TECH_100,
                "us-tech-100",
                "IX.D.NASDAQ.IFD.IP",
            ),
            IGMarketFamilyDefinition(
                CanonicalUnderlyingId.FRANCE_40,
                "indices",
                "IX.D.CAC.IFD.IP",
            ),
        )
    )

    with pytest.raises(MarketNavigationCatalogError, match="multiple canonical"):
        registry.resolve(
            page=_us_tech_page(),
            product_epic="IX.D.NASDAQ.OPTCALL2.IP",
        )


def test_registry_rejects_duplicate_canonical_or_node_definitions() -> None:
    first = IGMarketFamilyDefinition(
        CanonicalUnderlyingId.US_TECH_100,
        "us-tech-100",
        "IX.D.NASDAQ.IFD.IP",
    )

    with pytest.raises(ValueError, match="canonical underlying"):
        IGMarketFamilyRegistry(
            (
                first,
                IGMarketFamilyDefinition(
                    CanonicalUnderlyingId.US_TECH_100,
                    "nasdaq-alt",
                    "IX.D.NASDAQ.CASH.IP",
                ),
            )
        )
    with pytest.raises(ValueError, match="family node"):
        IGMarketFamilyRegistry(
            (
                first,
                IGMarketFamilyDefinition(
                    CanonicalUnderlyingId.FRANCE_40,
                    "us-tech-100",
                    "IX.D.CAC.IFD.IP",
                ),
            )
        )


def test_demo_category_path_is_lazy_and_resolves_exact_reference_metadata() -> None:
    catalog = LazyIGCategoryCatalog(SyntheticIGCategoryAdapter())
    categories = catalog.list_categories()
    indices = catalog.browse_category("INDICES")
    registry = IGReferenceMarketRegistry(
        (
            IGReferenceMarketDefinition(
                canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
                category_code="INDICES",
                underlying_name="US Tech 100",
                reference_epic="IX.D.NASDAQ.IFD.IP",
            ),
        )
    )

    resolved = registry.resolve(
        page=indices,
        canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
    )

    assert [category.category_id for category in categories] == ["INDICES", "COMMODITIES"]
    assert resolved.reference_epic == "IX.D.NASDAQ.IFD.IP"
    assert resolved.underlying_name == "US Tech 100"
    assert resolved.provenance[0] == "ig:categories"


def test_category_and_reference_mismatches_fail_closed() -> None:
    catalog = LazyIGCategoryCatalog(SyntheticIGCategoryAdapter())
    with pytest.raises(MarketNavigationCatalogError, match="first be loaded"):
        catalog.browse_category("INDICES")
    catalog.list_categories()
    indices = catalog.browse_category("INDICES")

    absent = IGReferenceMarketRegistry(
        (
            IGReferenceMarketDefinition(
                CanonicalUnderlyingId.US_TECH_100,
                "INDICES",
                "US Tech 100",
                "UNKNOWN.EPIC",
            ),
        )
    )
    wrong_name = IGReferenceMarketRegistry(
        (
            IGReferenceMarketDefinition(
                CanonicalUnderlyingId.US_TECH_100,
                "INDICES",
                "Nasdaq guessed name",
                "IX.D.NASDAQ.IFD.IP",
            ),
        )
    )

    with pytest.raises(MarketNavigationCatalogError, match="absent"):
        absent.resolve(
            page=indices,
            canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
        )
    with pytest.raises(MarketNavigationCatalogError, match="does not match"):
        wrong_name.resolve(
            page=indices,
            canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
        )


def test_product_market_binding_registry_requires_an_exact_epic() -> None:
    binding = IGProductMarketBinding(
        product_epic="IX.D.NASDAQ.OPTCALL2.IP",
        canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
        reference_epic="IX.D.NASDAQ.IFD.IP",
        provenance=("operator:explicit", "ig:demo-read-only"),
    )
    registry = IGProductMarketBindingRegistry((binding,))

    assert registry.resolve("IX.D.NASDAQ.OPTCALL2.IP") is binding
    with pytest.raises(MarketNavigationCatalogError, match="no explicit"):
        registry.resolve("US Tech 100 Barrières Achat")


def test_product_market_binding_registry_rejects_duplicate_product_epics() -> None:
    binding = IGProductMarketBinding(
        product_epic="IX.D.NASDAQ.OPTCALL2.IP",
        canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
        reference_epic="IX.D.NASDAQ.IFD.IP",
        provenance=("fixture:first",),
    )

    with pytest.raises(ValueError, match="multiple explicit"):
        IGProductMarketBindingRegistry(
            (
                binding,
                IGProductMarketBinding(
                    product_epic=binding.product_epic,
                    canonical_underlying_id=CanonicalUnderlyingId.FRANCE_40,
                    reference_epic="IX.D.CAC.IMF.IP",
                    provenance=("fixture:conflict",),
                ),
            )
        )


def test_initial_reference_universe_is_exact_stable_and_canonical() -> None:
    assert tuple(item[0] for item in INITIAL_IG_REFERENCE_EPICS) == tuple(CanonicalUnderlyingId)
    assert initial_ig_reference_epics() == (
        "IX.D.NASDAQ.IFD.IP",
        "IX.D.CAC.IMF.IP",
        "IX.D.DAX.IFMM.IP",
        "CS.D.CFEGOLD.CEF.IP",
        "CC.D.CL.UEF.IP",
    )
