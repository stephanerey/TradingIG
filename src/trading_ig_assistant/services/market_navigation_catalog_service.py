"""Lazy IG-style market navigation with explicit family resolution."""

from __future__ import annotations

from typing import Protocol

from trading_ig_assistant.domain.instruments import (
    MarketCategory,
    MarketNavigation,
    MarketSummary,
)
from trading_ig_assistant.domain.market_navigation import (
    IGCategoryPage,
    IGMarketFamilyDefinition,
    IGProductMarketBinding,
    IGReferenceMarketDefinition,
    MarketNavigationPage,
    NavigationPathNode,
    ResolvedIGProductLineage,
    ResolvedIGReferenceMarket,
)
from trading_ig_assistant.domain.markets import CanonicalUnderlyingId


class MarketNavigationAdapter(Protocol):
    def get_market_navigation(self, node_id: str | None = None) -> MarketNavigation:
        """Return one IG navigation page only."""


class IGCategoryAdapter(Protocol):
    def get_categories(self) -> list[MarketCategory]:
        """Return the account's available IG category codes."""

    def get_category_instruments(self, category_id: str) -> list[MarketSummary]:
        """Return one explicitly selected category page."""


class MarketNavigationCatalogError(ValueError):
    """Raised when IG navigation lineage is absent or ambiguous."""


class LazyMarketNavigationCatalog:
    """Browse one page at a time and retain the exact IG parent path in memory."""

    def __init__(self, adapter: MarketNavigationAdapter) -> None:
        self._adapter = adapter
        self._paths: dict[str, tuple[NavigationPathNode, ...]] = {}

    def browse_root(self) -> MarketNavigationPage:
        return self._build_page(None, (), self._adapter.get_market_navigation())

    def browse_node(self, node_id: str) -> MarketNavigationPage:
        try:
            breadcrumb = self._paths[node_id]
        except KeyError as exc:
            raise MarketNavigationCatalogError(
                "navigation node must first be discovered from its IG parent"
            ) from exc
        return self._build_page(
            node_id,
            breadcrumb,
            self._adapter.get_market_navigation(node_id),
        )

    def _build_page(
        self,
        node_id: str | None,
        breadcrumb: tuple[NavigationPathNode, ...],
        navigation: MarketNavigation,
    ) -> MarketNavigationPage:
        page = MarketNavigationPage(
            node_id=node_id,
            breadcrumb=breadcrumb,
            child_nodes=tuple(navigation.nodes),
            markets=tuple(navigation.markets),
        )
        for child in page.child_nodes:
            child_path = (
                *breadcrumb,
                NavigationPathNode(node_id=child.node_id, name=child.name),
            )
            previous = self._paths.get(child.node_id)
            if previous is not None and previous != child_path:
                raise MarketNavigationCatalogError(
                    "IG navigation node appeared under conflicting parent paths"
                )
            self._paths[child.node_id] = child_path
        return page


class IGMarketFamilyRegistry:
    """Resolve a product only from its verified IG navigation ancestry."""

    def __init__(self, definitions: tuple[IGMarketFamilyDefinition, ...]) -> None:
        canonical_ids = [definition.canonical_underlying_id for definition in definitions]
        node_ids = [definition.family_node_id for definition in definitions]
        if len(set(canonical_ids)) != len(canonical_ids):
            raise ValueError("canonical underlying has multiple IG family definitions")
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("IG family node has multiple canonical definitions")
        self._definitions = definitions

    def resolve(
        self,
        *,
        page: MarketNavigationPage,
        product_epic: str,
    ) -> ResolvedIGProductLineage:
        if not any(market.epic == product_epic for market in page.markets):
            raise MarketNavigationCatalogError("product EPIC is not present on this IG page")
        path_ids = {node.node_id for node in page.breadcrumb}
        matches = tuple(
            definition for definition in self._definitions if definition.family_node_id in path_ids
        )
        if not matches:
            raise MarketNavigationCatalogError(
                "product has no explicit canonical family in its IG navigation path"
            )
        if len(matches) != 1:
            raise MarketNavigationCatalogError(
                "product matches multiple canonical families in its IG navigation path"
            )
        definition = matches[0]
        return ResolvedIGProductLineage(
            product_epic=product_epic,
            canonical_underlying_id=definition.canonical_underlying_id,
            reference_epic=definition.reference_epic,
            navigation_path=page.breadcrumb,
            provenance=(
                "ig:market-navigation",
                "mapping:explicit-family-node",
                f"family_node:{definition.family_node_id}",
                f"reference_epic:{definition.reference_epic}",
            ),
        )


class LazyIGCategoryCatalog:
    """Use the category endpoints observed on IG DEMO without a full catalog crawl."""

    def __init__(self, adapter: IGCategoryAdapter) -> None:
        self._adapter = adapter
        self._categories: dict[str, MarketCategory] = {}

    def list_categories(self) -> tuple[MarketCategory, ...]:
        categories = tuple(self._adapter.get_categories())
        codes = [category.category_id for category in categories]
        if any(not code.strip() for code in codes):
            raise MarketNavigationCatalogError("IG returned a category without a code")
        if len(set(codes)) != len(codes):
            raise MarketNavigationCatalogError("IG returned duplicate category codes")
        self._categories = {category.category_id: category for category in categories}
        return categories

    def browse_category(self, category_code: str) -> IGCategoryPage:
        try:
            category = self._categories[category_code]
        except KeyError as exc:
            raise MarketNavigationCatalogError(
                "IG category must first be loaded from the category root"
            ) from exc
        return IGCategoryPage(
            category=category,
            markets=tuple(self._adapter.get_category_instruments(category_code)),
        )


class IGReferenceMarketRegistry:
    """Validate configured reference feeds against exact IG category metadata."""

    def __init__(self, definitions: tuple[IGReferenceMarketDefinition, ...]) -> None:
        canonical_ids = [definition.canonical_underlying_id for definition in definitions]
        epics = [definition.reference_epic for definition in definitions]
        if len(set(canonical_ids)) != len(canonical_ids):
            raise ValueError("canonical underlying has multiple reference-market definitions")
        if len(set(epics)) != len(epics):
            raise ValueError("reference EPIC is assigned to multiple canonical underlyings")
        self._by_canonical = {
            definition.canonical_underlying_id: definition for definition in definitions
        }

    def resolve(
        self,
        *,
        page: IGCategoryPage,
        canonical_underlying_id: CanonicalUnderlyingId,
    ) -> ResolvedIGReferenceMarket:
        try:
            definition = self._by_canonical[canonical_underlying_id]
        except KeyError as exc:
            raise MarketNavigationCatalogError(
                "canonical underlying has no explicit IG reference market"
            ) from exc
        if page.category.category_id != definition.category_code:
            raise MarketNavigationCatalogError("IG reference market category does not match")
        market = next(
            (market for market in page.markets if market.epic == definition.reference_epic),
            None,
        )
        if market is None:
            raise MarketNavigationCatalogError("configured reference EPIC is absent from IG page")
        if market.raw.get("underlyingName") != definition.underlying_name:
            raise MarketNavigationCatalogError(
                "configured reference underlying name does not match IG metadata"
            )
        return ResolvedIGReferenceMarket(
            canonical_underlying_id=canonical_underlying_id,
            category_code=definition.category_code,
            underlying_name=definition.underlying_name,
            reference_epic=definition.reference_epic,
            provenance=(
                "ig:categories",
                f"category:{definition.category_code}",
                f"underlying_name:{definition.underlying_name}",
                f"reference_epic:{definition.reference_epic}",
            ),
        )


class IGProductMarketBindingRegistry:
    """Resolve only exact product EPICs; never infer a parent from names or EPIC patterns."""

    def __init__(self, bindings: tuple[IGProductMarketBinding, ...]) -> None:
        product_epics = [binding.product_epic for binding in bindings]
        if len(set(product_epics)) != len(product_epics):
            raise ValueError("IG product EPIC has multiple explicit market bindings")
        self._by_product_epic = {binding.product_epic: binding for binding in bindings}

    def resolve(self, product_epic: str) -> IGProductMarketBinding:
        if not product_epic.strip():
            raise MarketNavigationCatalogError("product EPIC is required")
        try:
            return self._by_product_epic[product_epic]
        except KeyError as exc:
            raise MarketNavigationCatalogError(
                "product EPIC has no explicit canonical market binding"
            ) from exc

    def bindings(self) -> tuple[IGProductMarketBinding, ...]:
        """Return the exact configured bindings in deterministic product order."""

        return tuple(self._by_product_epic[epic] for epic in sorted(self._by_product_epic))

    def for_reference_epic(self, reference_epic: str) -> tuple[IGProductMarketBinding, ...]:
        if not reference_epic.strip():
            raise MarketNavigationCatalogError("reference EPIC is required")
        return tuple(
            sorted(
                (
                    binding
                    for binding in self._by_product_epic.values()
                    if binding.reference_epic == reference_epic
                ),
                key=lambda binding: binding.product_epic,
            )
        )
