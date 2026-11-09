"""Typed, secret-free scanner strategy profile persistence contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from trading_ig_assistant.domain.analysis import StrategyId
from trading_ig_assistant.domain.markets import CanonicalUnderlyingId


@dataclass(frozen=True)
class ScannerProfilePatch:
    """One identified set of leaf-level profile overrides."""

    patch_id: str
    overrides: tuple[tuple[str, object], ...]

    def __post_init__(self) -> None:
        if not self.patch_id.strip():
            raise ValueError("scanner profile patch ID is required")
        if self.patch_id != self.patch_id.strip():
            raise ValueError("scanner profile patch ID must not contain surrounding whitespace")
        if not self.overrides:
            raise ValueError("scanner profile patch must contain at least one override")
        paths = tuple(path.strip() for path, _value in self.overrides)
        if any(
            not path or path == "profile_id" or path.startswith("profile_id.") for path in paths
        ):
            raise ValueError("scanner profile patch path is invalid")
        if len(set(paths)) != len(paths):
            raise ValueError("scanner profile patch contains duplicate paths")
        if paths != tuple(path for path, _value in self.overrides):
            raise ValueError("scanner profile patch paths must not contain surrounding whitespace")

    def to_file_dict(self) -> dict[str, object]:
        return {
            "patch_id": self.patch_id,
            "overrides": [
                {"path": path, "value": _encode_override_value(value)}
                for path, value in self.overrides
            ],
        }

    @classmethod
    def from_mapping(cls, data: object) -> ScannerProfilePatch:
        mapping = _mapping(data, "scanner profile patch")
        patch_id = _required_text(mapping.get("patch_id"), "scanner profile patch ID")
        raw_overrides = mapping.get("overrides")
        if not isinstance(raw_overrides, list):
            raise ValueError("scanner profile patch overrides must be a list")
        overrides: list[tuple[str, object]] = []
        for index, raw_override in enumerate(raw_overrides):
            override = _mapping(raw_override, f"scanner profile override {index}")
            path = _required_text(override.get("path"), f"scanner profile override {index} path")
            if "value" not in override:
                raise ValueError(f"scanner profile override {index} value is required")
            overrides.append((path, _decode_override_value(override["value"])))
        return cls(patch_id=patch_id, overrides=tuple(overrides))


@dataclass(frozen=True)
class ScannerProfileCatalog:
    """Immutable exact-key patches for the approved scanner profile hierarchy."""

    global_patch: ScannerProfilePatch | None = None
    account_patches: tuple[tuple[str, ScannerProfilePatch], ...] = ()
    strategy_patches: tuple[tuple[StrategyId, ScannerProfilePatch], ...] = ()
    market_patches: tuple[tuple[CanonicalUnderlyingId, ScannerProfilePatch], ...] = ()

    def __post_init__(self) -> None:
        _validate_text_patch_entries(self.account_patches, label="IG account ID")
        _validate_strategy_patch_entries(self.strategy_patches)
        _validate_market_patch_entries(self.market_patches)

    def account_patch_for(self, account_id: str | None) -> ScannerProfilePatch | None:
        if account_id is None:
            return None
        key = _required_text(account_id, "IG account ID")
        return dict(self.account_patches).get(key)

    def strategy_patch_for(self, strategy_id: StrategyId) -> ScannerProfilePatch | None:
        if not isinstance(strategy_id, StrategyId):
            raise ValueError("scanner profile strategy key must be a StrategyId")
        return dict(self.strategy_patches).get(strategy_id)

    def market_patch_for(
        self,
        canonical_underlying_id: CanonicalUnderlyingId,
    ) -> ScannerProfilePatch | None:
        if not isinstance(canonical_underlying_id, CanonicalUnderlyingId):
            raise ValueError("scanner profile market key must be a CanonicalUnderlyingId")
        return dict(self.market_patches).get(canonical_underlying_id)

    def to_file_dict(self) -> dict[str, object]:
        return {
            "global": self.global_patch.to_file_dict() if self.global_patch else None,
            "accounts": {key: patch.to_file_dict() for key, patch in sorted(self.account_patches)},
            "strategies": {
                key.value: patch.to_file_dict()
                for key, patch in sorted(self.strategy_patches, key=lambda item: item[0].value)
            },
            "markets": {
                key.value: patch.to_file_dict()
                for key, patch in sorted(self.market_patches, key=lambda item: item[0].value)
            },
        }

    @classmethod
    def from_mapping(cls, data: object) -> ScannerProfileCatalog:
        mapping = _mapping(data, "scanner profile catalog")
        global_data = mapping.get("global")
        return cls(
            global_patch=(
                ScannerProfilePatch.from_mapping(global_data) if global_data is not None else None
            ),
            account_patches=_parse_text_patch_map(mapping.get("accounts", {}), "IG account"),
            strategy_patches=_parse_strategy_patch_map(mapping.get("strategies", {})),
            market_patches=_parse_market_patch_map(mapping.get("markets", {})),
        )


def _encode_override_value(value: object) -> dict[str, object]:
    if value is None:
        return {"type": "null", "value": None}
    if isinstance(value, bool):
        raise ValueError("boolean scanner profile override values are unsupported")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("scanner profile decimal override must be finite")
        return {"type": "decimal", "value": format(value, "f")}
    if isinstance(value, int):
        return {"type": "integer", "value": value}
    if isinstance(value, str):
        return {"type": "string", "value": value}
    if isinstance(value, timedelta):
        total_microseconds = (value.days * 86400 + value.seconds) * 1_000_000 + value.microseconds
        seconds = Decimal(total_microseconds) / Decimal("1000000")
        return {"type": "duration_seconds", "value": format(seconds, "f")}
    if isinstance(value, tuple) and all(isinstance(item, StrategyId) for item in value):
        return {"type": "strategy_ids", "value": [item.value for item in value]}
    if isinstance(value, tuple) and all(isinstance(item, Decimal) for item in value):
        if any(not item.is_finite() for item in value):
            raise ValueError("scanner profile decimal tuple override must be finite")
        return {"type": "decimal_tuple", "value": [format(item, "f") for item in value]}
    raise ValueError(f"unsupported scanner profile override type: {type(value).__name__}")


def _decode_override_value(data: object) -> object:
    mapping = _mapping(data, "scanner profile override value")
    value_type = _required_text(mapping.get("type"), "scanner profile override value type")
    if "value" not in mapping:
        raise ValueError("scanner profile override typed value is required")
    value = mapping["value"]
    if value_type == "null":
        if value is not None:
            raise ValueError("scanner profile null override must contain null")
        return None
    if value_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("scanner profile integer override must contain an integer")
        return value
    if value_type == "string":
        if not isinstance(value, str):
            raise ValueError("scanner profile string override must contain text")
        return value
    if value_type == "decimal":
        return _decimal(value, "scanner profile decimal override")
    if value_type == "duration_seconds":
        seconds = _decimal(value, "scanner profile duration override")
        if seconds <= 0:
            raise ValueError("scanner profile duration override must be positive")
        microseconds = seconds * Decimal("1000000")
        if microseconds != microseconds.to_integral_value():
            raise ValueError("scanner profile duration exceeds microsecond precision")
        return timedelta(microseconds=int(microseconds))
    if value_type == "strategy_ids":
        if not isinstance(value, list):
            raise ValueError("scanner profile strategy override must contain a list")
        try:
            return tuple(StrategyId(item) for item in value)
        except (TypeError, ValueError) as exc:
            raise ValueError("scanner profile strategy override contains an invalid ID") from exc
    if value_type == "decimal_tuple":
        if not isinstance(value, list):
            raise ValueError("scanner profile decimal tuple override must contain a list")
        return tuple(_decimal(item, "scanner profile decimal tuple item") for item in value)
    raise ValueError(f"unsupported scanner profile override value type: {value_type}")


def _parse_text_patch_map(
    data: object,
    label: str,
) -> tuple[tuple[str, ScannerProfilePatch], ...]:
    mapping = _mapping(data, f"scanner profile {label} patches")
    return tuple(
        (key, ScannerProfilePatch.from_mapping(value)) for key, value in sorted(mapping.items())
    )


def _parse_strategy_patch_map(
    data: object,
) -> tuple[tuple[StrategyId, ScannerProfilePatch], ...]:
    mapping = _mapping(data, "scanner profile strategy patches")
    try:
        return tuple(
            (StrategyId(key), ScannerProfilePatch.from_mapping(value))
            for key, value in sorted(mapping.items())
        )
    except ValueError as exc:
        raise ValueError("scanner profile catalog contains an invalid StrategyId key") from exc


def _parse_market_patch_map(
    data: object,
) -> tuple[tuple[CanonicalUnderlyingId, ScannerProfilePatch], ...]:
    mapping = _mapping(data, "scanner profile canonical underlying patches")
    try:
        return tuple(
            (CanonicalUnderlyingId(key), ScannerProfilePatch.from_mapping(value))
            for key, value in sorted(mapping.items())
        )
    except ValueError as exc:
        raise ValueError(
            "scanner profile catalog contains an invalid canonical underlying key"
        ) from exc


def _validate_text_patch_entries(
    entries: tuple[tuple[str, ScannerProfilePatch], ...],
    *,
    label: str,
) -> None:
    keys = tuple(key for key, _patch in entries)
    for key, patch in entries:
        _required_text(key, label)
        if not isinstance(patch, ScannerProfilePatch):
            raise ValueError(f"{label} scanner profile value must be a patch")
    if len(set(keys)) != len(keys):
        raise ValueError(f"scanner profile catalog contains duplicate {label} keys")


def _validate_strategy_patch_entries(
    entries: tuple[tuple[StrategyId, ScannerProfilePatch], ...],
) -> None:
    keys = tuple(key for key, _patch in entries)
    for key, patch in entries:
        if not isinstance(key, StrategyId):
            raise ValueError("scanner profile strategy key must be a StrategyId")
        if key is StrategyId.EVENT_DRIVEN:
            raise ValueError("event-driven strategy configuration is not a technical profile patch")
        if not isinstance(patch, ScannerProfilePatch):
            raise ValueError("strategy scanner profile value must be a patch")
    if len(set(keys)) != len(keys):
        raise ValueError("scanner profile catalog contains duplicate StrategyId keys")


def _validate_market_patch_entries(
    entries: tuple[tuple[CanonicalUnderlyingId, ScannerProfilePatch], ...],
) -> None:
    keys = tuple(key for key, _patch in entries)
    for key, patch in entries:
        if not isinstance(key, CanonicalUnderlyingId):
            raise ValueError("scanner profile market key must be a CanonicalUnderlyingId")
        if not isinstance(patch, ScannerProfilePatch):
            raise ValueError("market scanner profile value must be a patch")
    if len(set(keys)) != len(keys):
        raise ValueError("scanner profile catalog contains duplicate canonical underlying keys")


def _mapping(data: object, label: str) -> dict[str, Any]:
    if not isinstance(data, dict) or any(not isinstance(key, str) for key in data):
        raise ValueError(f"{label} must be a JSON object")
    return data


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    if value != value.strip():
        raise ValueError(f"{label} must not contain surrounding whitespace")
    return value


def _decimal(value: object, label: str) -> Decimal:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be stored as text")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{label} is invalid") from exc
    if not parsed.is_finite():
        raise ValueError(f"{label} must be finite")
    return parsed
