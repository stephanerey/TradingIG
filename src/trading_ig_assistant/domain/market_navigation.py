"""Typed IG navigation lineage and explicit canonical-market bindings."""

from __future__ import annotations

from dataclasses import dataclass

from trading_ig_assistant.domain.instruments import (
    MarketCategory,
    MarketNavigationNode,
    MarketSummary,
)
from trading_ig_assistant.domain.markets import CanonicalUnderlyingId

INITIAL_IG_REFERENCE_EPICS: tuple[tuple[CanonicalUnderlyingId, str], ...] = (
    (CanonicalUnderlyingId.US_TECH_100, "IX.D.NASDAQ.IFD.IP"),
    (CanonicalUnderlyingId.FRANCE_40, "IX.D.CAC.IMF.IP"),
    (CanonicalUnderlyingId.GERMANY_40, "IX.D.DAX.IFMM.IP"),
    (CanonicalUnderlyingId.SPOT_GOLD, "CS.D.CFEGOLD.CEF.IP"),
    (CanonicalUnderlyingId.US_CRUDE, "CC.D.CL.UEF.IP"),
)


def initial_ig_reference_epics() -> tuple[str, ...]:
    """Return the human-approved initial Scanner reference universe in stable order."""

    return tuple(reference_epic for _underlying, reference_epic in INITIAL_IG_REFERENCE_EPICS)


@dataclass(frozen=True)
class NavigationPathNode:
    node_id: str
    name: str

    def __post_init__(self) -> None:
        if not self.node_id.strip() or not self.name.strip():
            raise ValueError("navigation path node identity and name are required")


@dataclass(frozen=True)
class MarketNavigationPage:
    node_id: str | None
    breadcrumb: tuple[NavigationPathNode, ...]
    child_nodes: tuple[MarketNavigationNode, ...]
    markets: tuple[MarketSummary, ...]

    def __post_init__(self) -> None:
        if self.node_id is None and self.breadcrumb:
            raise ValueError("root navigation page cannot have a breadcrumb")
        if self.node_id is not None:
            if not self.breadcrumb or self.breadcrumb[-1].node_id != self.node_id:
                raise ValueError("navigation page breadcrumb must end at its node")
        child_ids = [node.node_id for node in self.child_nodes]
        market_epics = [market.epic for market in self.markets]
        if any(not value.strip() for value in (*child_ids, *market_epics)):
            raise ValueError("navigation page contains an empty node or market identity")
        if len(set(child_ids)) != len(child_ids):
            raise ValueError("navigation page contains duplicate child nodes")
        if len(set(market_epics)) != len(market_epics):
            raise ValueError("navigation page contains duplicate market EPICs")


@dataclass(frozen=True)
class IGMarketFamilyDefinition:
    canonical_underlying_id: CanonicalUnderlyingId
    family_node_id: str
    reference_epic: str

    def __post_init__(self) -> None:
        if not isinstance(self.canonical_underlying_id, CanonicalUnderlyingId):
            raise TypeError("market family requires a canonical underlying ID")
        if not self.family_node_id.strip() or not self.reference_epic.strip():
            raise ValueError("market family node and reference EPIC are required")


@dataclass(frozen=True)
class ResolvedIGProductLineage:
    product_epic: str
    canonical_underlying_id: CanonicalUnderlyingId
    reference_epic: str
    navigation_path: tuple[NavigationPathNode, ...]
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.product_epic.strip() or not self.reference_epic.strip():
            raise ValueError("resolved IG product and reference EPICs are required")
        if not self.navigation_path:
            raise ValueError("resolved IG product requires navigation lineage")
        if not self.provenance:
            raise ValueError("resolved IG product provenance is required")


@dataclass(frozen=True)
class IGCategoryPage:
    category: MarketCategory
    markets: tuple[MarketSummary, ...]

    def __post_init__(self) -> None:
        if not self.category.category_id.strip():
            raise ValueError("IG category code is required")
        epics = [market.epic for market in self.markets]
        if any(not epic.strip() for epic in epics):
            raise ValueError("IG category contains an empty market EPIC")
        if len(set(epics)) != len(epics):
            raise ValueError("IG category contains duplicate market EPICs")


@dataclass(frozen=True)
class IGReferenceMarketDefinition:
    canonical_underlying_id: CanonicalUnderlyingId
    category_code: str
    underlying_name: str
    reference_epic: str

    def __post_init__(self) -> None:
        if not isinstance(self.canonical_underlying_id, CanonicalUnderlyingId):
            raise TypeError("reference market requires a canonical underlying ID")
        required = (self.category_code, self.underlying_name, self.reference_epic)
        if any(not value.strip() for value in required):
            raise ValueError("reference market category, underlying name and EPIC are required")


@dataclass(frozen=True)
class ResolvedIGReferenceMarket:
    canonical_underlying_id: CanonicalUnderlyingId
    category_code: str
    underlying_name: str
    reference_epic: str
    provenance: tuple[str, ...]


@dataclass(frozen=True)
class IGProductMarketBinding:
    """Explicit product-to-underlying relation supplied by verified configuration/evidence."""

    product_epic: str
    canonical_underlying_id: CanonicalUnderlyingId
    reference_epic: str
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.canonical_underlying_id, CanonicalUnderlyingId):
            raise TypeError("product market binding requires a canonical underlying ID")
        if not self.product_epic.strip() or not self.reference_epic.strip():
            raise ValueError("product and reference EPICs are required")
        if not self.provenance or any(not item.strip() for item in self.provenance):
            raise ValueError("product market binding provenance is required")
