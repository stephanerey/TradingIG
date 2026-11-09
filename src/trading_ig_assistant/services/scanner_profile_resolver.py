"""Resolve scanner strategy parameters with explicit layered provenance."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from typing import Any

from trading_ig_assistant.domain.adapter_contracts import InstrumentMappingRegistry
from trading_ig_assistant.domain.analysis import TECHNICAL_STRATEGY_IDS, StrategyId
from trading_ig_assistant.domain.markets import CanonicalUnderlyingId
from trading_ig_assistant.domain.scanner_profiles import (
    ScannerProfileCatalog,
    ScannerProfilePatch,
)
from trading_ig_assistant.services.scanner_preview_service import (
    ScannerStrategyProfile,
    default_scanner_strategy_profile,
)


@dataclass(frozen=True)
class ResolvedScannerStrategyProfile:
    profile: ScannerStrategyProfile
    sources: tuple[tuple[str, str], ...]

    def source_for(self, path: str) -> str:
        return dict(self.sources)[path]


def resolve_scanner_strategy_profile(
    *,
    base_profile: ScannerStrategyProfile | None = None,
    global_patch: ScannerProfilePatch | None = None,
    account_patch: ScannerProfilePatch | None = None,
    strategy_patch: ScannerProfilePatch | None = None,
    market_patch: ScannerProfilePatch | None = None,
) -> ResolvedScannerStrategyProfile:
    """Apply explicit leaf patches in the approved precedence order.

    This service does not choose which account, strategy or market patch applies. Callers must
    resolve those identities explicitly before invoking it.
    """

    profile = base_profile or default_scanner_strategy_profile()
    source_by_path = {path: "default" for path in _leaf_paths(profile)}
    applied: list[tuple[str, str]] = []
    for layer_name, patch in (
        ("global", global_patch),
        ("account", account_patch),
        ("strategy", strategy_patch),
        ("market", market_patch),
    ):
        if patch is None:
            continue
        profile = _apply_patch(profile, patch)
        source = f"{layer_name}:{patch.patch_id}"
        for path, _value in patch.overrides:
            source_by_path[path] = source
        applied.append((layer_name, patch.patch_id))

    if applied:
        resolved_id = "|".join(
            (profile.profile_id, *(f"{layer}={patch_id}" for layer, patch_id in applied))
        )
        profile = replace(profile, profile_id=resolved_id)
        source_by_path["profile_id"] = "resolver"

    ordered_paths = ("profile_id", *_leaf_paths(profile))
    sources = tuple((path, source_by_path.get(path, "default")) for path in ordered_paths)
    return ResolvedScannerStrategyProfile(profile=profile, sources=sources)


def resolve_scanner_profile_from_catalog(
    catalog: ScannerProfileCatalog,
    *,
    strategy_id: StrategyId,
    canonical_underlying_id: CanonicalUnderlyingId,
    account_id: str | None = None,
    base_profile: ScannerStrategyProfile | None = None,
) -> ResolvedScannerStrategyProfile:
    """Resolve exact validated catalog keys without inferring product relationships."""

    if not isinstance(catalog, ScannerProfileCatalog):
        raise ValueError("scanner profile catalog is required")
    if not isinstance(strategy_id, StrategyId):
        raise ValueError("scanner profile strategy key must be a StrategyId")
    if strategy_id is StrategyId.EVENT_DRIVEN:
        raise ValueError("event-driven strategy configuration is not a technical profile patch")
    if not isinstance(canonical_underlying_id, CanonicalUnderlyingId):
        raise ValueError("scanner profile market key must be a CanonicalUnderlyingId")
    return resolve_scanner_strategy_profile(
        base_profile=base_profile,
        global_patch=catalog.global_patch,
        account_patch=catalog.account_patch_for(account_id),
        strategy_patch=catalog.strategy_patch_for(strategy_id),
        market_patch=catalog.market_patch_for(canonical_underlying_id),
    )


def resolve_scanner_profile_for_instrument(
    catalog: ScannerProfileCatalog,
    mapping_registry: InstrumentMappingRegistry,
    *,
    provider_id: str,
    instrument_id: str,
    strategy_id: StrategyId,
    account_id: str | None = None,
    base_profile: ScannerStrategyProfile | None = None,
) -> ResolvedScannerStrategyProfile:
    """Resolve the market layer only through an explicit provider instrument mapping."""

    mapping = mapping_registry.resolve(provider_id, instrument_id)
    try:
        canonical_underlying_id = CanonicalUnderlyingId(mapping.underlying_id)
    except ValueError as exc:
        raise ValueError(
            "explicit instrument mapping contains an unsupported canonical underlying ID"
        ) from exc
    return resolve_scanner_profile_from_catalog(
        catalog,
        account_id=account_id,
        strategy_id=strategy_id,
        canonical_underlying_id=canonical_underlying_id,
        base_profile=base_profile,
    )


def resolve_scanner_profiles_from_catalog(
    catalog: ScannerProfileCatalog,
    *,
    canonical_underlying_id: CanonicalUnderlyingId,
    account_id: str | None = None,
    strategy_ids: tuple[StrategyId, ...] = TECHNICAL_STRATEGY_IDS,
    base_profile: ScannerStrategyProfile | None = None,
) -> tuple[ResolvedScannerStrategyProfile, ...]:
    """Resolve one provenance-rich single-strategy profile per requested technical strategy."""

    _validate_technical_strategy_selection(strategy_ids)
    common_base = base_profile or default_scanner_strategy_profile()
    resolved_profiles: list[ResolvedScannerStrategyProfile] = []
    selected = set(strategy_ids)
    for strategy_id in (item for item in TECHNICAL_STRATEGY_IDS if item in selected):
        strategy_base = replace(
            common_base,
            profile_id=f"{common_base.profile_id}:selected={strategy_id.value}",
            enabled_strategies=(strategy_id,),
        )
        resolved = resolve_scanner_profile_from_catalog(
            catalog,
            account_id=account_id,
            strategy_id=strategy_id,
            canonical_underlying_id=canonical_underlying_id,
            base_profile=strategy_base,
        )
        if resolved.profile.enabled_strategies != (strategy_id,):
            raise ValueError(
                "layered scanner profile changed the explicit single-strategy selection"
            )
        sources = tuple(
            (path, f"selector:{strategy_id.value}" if path == "enabled_strategies" else source)
            for path, source in resolved.sources
        )
        resolved_profiles.append(
            ResolvedScannerStrategyProfile(profile=resolved.profile, sources=sources)
        )
    return tuple(resolved_profiles)


def resolve_scanner_profiles_for_instrument(
    catalog: ScannerProfileCatalog,
    mapping_registry: InstrumentMappingRegistry,
    *,
    provider_id: str,
    instrument_id: str,
    account_id: str | None = None,
    strategy_ids: tuple[StrategyId, ...] = TECHNICAL_STRATEGY_IDS,
    base_profile: ScannerStrategyProfile | None = None,
) -> tuple[ResolvedScannerStrategyProfile, ...]:
    """Resolve all requested technical profiles through one explicit instrument mapping."""

    mapping = mapping_registry.resolve(provider_id, instrument_id)
    try:
        canonical_underlying_id = CanonicalUnderlyingId(mapping.underlying_id)
    except ValueError as exc:
        raise ValueError(
            "explicit instrument mapping contains an unsupported canonical underlying ID"
        ) from exc
    return resolve_scanner_profiles_from_catalog(
        catalog,
        account_id=account_id,
        strategy_ids=strategy_ids,
        canonical_underlying_id=canonical_underlying_id,
        base_profile=base_profile,
    )


def _validate_technical_strategy_selection(strategy_ids: tuple[StrategyId, ...]) -> None:
    if not strategy_ids:
        raise ValueError("multi-strategy scanner selection must not be empty")
    if any(not isinstance(strategy_id, StrategyId) for strategy_id in strategy_ids):
        raise ValueError("multi-strategy scanner selection must contain StrategyId values")
    if len(set(strategy_ids)) != len(strategy_ids):
        raise ValueError("multi-strategy scanner selection must be unique")
    unsupported = set(strategy_ids).difference(TECHNICAL_STRATEGY_IDS)
    if unsupported:
        raise ValueError("multi-strategy technical scanner does not accept EVENT_DRIVEN")


def _apply_patch(
    profile: ScannerStrategyProfile,
    patch: ScannerProfilePatch,
) -> ScannerStrategyProfile:
    override_tree: dict[str, Any] = {}
    for path, value in patch.overrides:
        cursor = override_tree
        parts = path.split(".")
        if any(not part for part in parts):
            raise ValueError(f"invalid scanner profile override path: {path}")
        for part in parts[:-1]:
            existing = cursor.get(part)
            if existing is not None and not isinstance(existing, dict):
                raise ValueError(f"conflicting scanner profile override path: {path}")
            cursor = cursor.setdefault(part, {})
        if parts[-1] in cursor:
            raise ValueError(f"conflicting scanner profile override path: {path}")
        cursor[parts[-1]] = value
    try:
        resolved = _replace_dataclass_leaves(profile, override_tree, prefix="")
    except (TypeError, AttributeError) as exc:
        raise ValueError(f"scanner profile patch {patch.patch_id!r} is invalid") from exc
    if not isinstance(resolved, ScannerStrategyProfile):
        raise ValueError("scanner profile patch did not resolve to a strategy profile")
    return resolved


def _replace_dataclass_leaves(instance: object, tree: dict[str, Any], *, prefix: str) -> object:
    if not is_dataclass(instance) or isinstance(instance, type):
        raise ValueError(f"scanner profile override does not target a dataclass: {prefix}")
    field_names = {item.name for item in fields(instance)}
    unknown = set(tree).difference(field_names)
    if unknown:
        path = f"{prefix}.{sorted(unknown)[0]}" if prefix else sorted(unknown)[0]
        raise ValueError(f"unknown scanner profile override path: {path}")

    updates: dict[str, object] = {}
    for field_name, override in tree.items():
        path = f"{prefix}.{field_name}" if prefix else field_name
        current = getattr(instance, field_name)
        if isinstance(override, dict):
            updates[field_name] = _replace_dataclass_leaves(current, override, prefix=path)
        else:
            if is_dataclass(current) and not isinstance(current, type):
                raise ValueError(f"scanner profile override must target a leaf: {path}")
            updates[field_name] = override
    return replace(instance, **updates)


def _leaf_paths(instance: object, *, prefix: str = "") -> tuple[str, ...]:
    if not is_dataclass(instance) or isinstance(instance, type):
        return (prefix,)
    paths: list[str] = []
    for item in fields(instance):
        if not prefix and item.name == "profile_id":
            continue
        path = f"{prefix}.{item.name}" if prefix else item.name
        value = getattr(instance, item.name)
        if is_dataclass(value) and not isinstance(value, type):
            paths.extend(_leaf_paths(value, prefix=path))
        else:
            paths.append(path)
    return tuple(paths)
