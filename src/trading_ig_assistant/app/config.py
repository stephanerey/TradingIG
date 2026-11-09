"""Application configuration model and JSON loading."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from typing import Any

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.domain.market_navigation import IGProductMarketBinding
from trading_ig_assistant.domain.markets import CanonicalUnderlyingId
from trading_ig_assistant.domain.scanner_profiles import ScannerProfileCatalog


class IGEnvironment(StrEnum):
    DEMO = "demo"
    LIVE = "live"


@dataclass
class IGConnectionProfileConfig:
    environment: IGEnvironment
    identifier: str = ""
    selected_account_id: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.environment, str):
            self.environment = IGEnvironment(self.environment.lower())

    def to_file_dict(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "selected_account_id": self.selected_account_id,
        }

    @classmethod
    def from_mapping(
        cls,
        environment: IGEnvironment,
        data: dict[str, Any],
    ) -> IGConnectionProfileConfig:
        return cls(
            environment=environment,
            identifier=str(data.get("identifier", "")),
            selected_account_id=data.get("selected_account_id") or None,
        )


@dataclass(frozen=True)
class WorkspaceState:
    window_width: int | None = None
    window_height: int | None = None
    splitter_sizes: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if self.window_width is not None and self.window_width <= 0:
            raise ValueError("window_width must be positive")
        if self.window_height is not None and self.window_height <= 0:
            raise ValueError("window_height must be positive")
        if any(size < 0 for size in self.splitter_sizes):
            raise ValueError("splitter_sizes must not contain negative values")

    def to_file_dict(self) -> dict[str, Any]:
        return {
            "window_width": self.window_width,
            "window_height": self.window_height,
            "splitter_sizes": list(self.splitter_sizes),
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> WorkspaceState:
        width = data.get("window_width")
        height = data.get("window_height")
        sizes = data.get("splitter_sizes", [])
        try:
            parsed_width = int(width) if width is not None else None
            parsed_height = int(height) if height is not None else None
            parsed_sizes = tuple(int(size) for size in sizes) if isinstance(sizes, list) else ()
            return cls(
                window_width=parsed_width,
                window_height=parsed_height,
                splitter_sizes=parsed_sizes,
            )
        except (TypeError, ValueError):
            return cls()


@dataclass(frozen=True)
class ScannerExecutionCostConfig:
    """Optional manual fee estimates used by the scanner cost component.

    Values are expressed in the product currency, per unit and per side. ``None`` is
    deliberately distinct from zero: it means that the operator has not qualified the
    product type yet and the scanner must keep the cost component unavailable.
    """

    cash_or_dfb_fee_per_unit_per_side: Decimal | None = None
    barrier_fee_per_unit_per_side: Decimal | None = None
    option_fee_per_unit_per_side: Decimal | None = None
    unknown_fee_per_unit_per_side: Decimal | None = None
    defaults_initialized: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "cash_or_dfb_fee_per_unit_per_side",
            "barrier_fee_per_unit_per_side",
            "option_fee_per_unit_per_side",
            "unknown_fee_per_unit_per_side",
        ):
            value = getattr(self, field_name)
            if value is not None and (not value.is_finite() or value < 0):
                raise ValueError(f"{field_name} must be a finite non-negative decimal")

    def fee_for_product_type(self, product_type: object) -> Decimal | None:
        product_type_value = str(getattr(product_type, "value", product_type)).lower()
        return {
            "cash_or_dfb": self.cash_or_dfb_fee_per_unit_per_side,
            "barrier": self.barrier_fee_per_unit_per_side,
            "option": self.option_fee_per_unit_per_side,
            "unknown": self.unknown_fee_per_unit_per_side,
        }.get(product_type_value, self.unknown_fee_per_unit_per_side)

    def to_file_dict(self) -> dict[str, str | bool | None]:
        return {
            "cash_or_dfb_fee_per_unit_per_side": _decimal_to_text(
                self.cash_or_dfb_fee_per_unit_per_side
            ),
            "barrier_fee_per_unit_per_side": _decimal_to_text(self.barrier_fee_per_unit_per_side),
            "option_fee_per_unit_per_side": _decimal_to_text(self.option_fee_per_unit_per_side),
            "unknown_fee_per_unit_per_side": _decimal_to_text(self.unknown_fee_per_unit_per_side),
            "defaults_initialized": self.defaults_initialized,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> ScannerExecutionCostConfig:
        return cls(
            cash_or_dfb_fee_per_unit_per_side=_safe_optional_decimal(
                data.get("cash_or_dfb_fee_per_unit_per_side")
            ),
            barrier_fee_per_unit_per_side=_safe_optional_decimal(
                data.get("barrier_fee_per_unit_per_side")
            ),
            option_fee_per_unit_per_side=_safe_optional_decimal(
                data.get("option_fee_per_unit_per_side")
            ),
            unknown_fee_per_unit_per_side=_safe_optional_decimal(
                data.get("unknown_fee_per_unit_per_side")
            ),
            defaults_initialized=bool(data.get("defaults_initialized", False)),
        )


@dataclass(frozen=True)
class ScannerScoringConfig:
    """Global editable PRD defaults for scanner ranking weights and thresholds."""

    technical_weight: Decimal = Decimal("30")
    context_weight: Decimal = Decimal("15")
    reward_risk_weight: Decimal = Decimal("20")
    market_risk_weight: Decimal = Decimal("15")
    execution_cost_weight: Decimal = Decimal("10")
    data_quality_weight: Decimal = Decimal("10")
    candidate_threshold: Decimal = Decimal("75")
    watch_threshold: Decimal = Decimal("60")

    def __post_init__(self) -> None:
        weights = self.component_weights()
        if any(not value.is_finite() or value < 0 for value in weights.values()):
            raise ValueError("scanner component weights must be finite and non-negative")
        if sum(weights.values(), Decimal("0")) <= 0:
            raise ValueError("scanner component weights must have a positive total")
        if not (
            self.watch_threshold.is_finite()
            and self.candidate_threshold.is_finite()
            and Decimal("0") <= self.watch_threshold <= self.candidate_threshold <= Decimal("100")
        ):
            raise ValueError("scanner thresholds must satisfy 0 <= watch <= candidate <= 100")

    def component_weights(self) -> dict[str, Decimal]:
        return {
            "technical": self.technical_weight,
            "context": self.context_weight,
            "reward_risk": self.reward_risk_weight,
            "market_risk": self.market_risk_weight,
            "execution_cost": self.execution_cost_weight,
            "data_quality": self.data_quality_weight,
        }

    def to_file_dict(self) -> dict[str, str]:
        return {
            "technical_weight": format(self.technical_weight, "f"),
            "context_weight": format(self.context_weight, "f"),
            "reward_risk_weight": format(self.reward_risk_weight, "f"),
            "market_risk_weight": format(self.market_risk_weight, "f"),
            "execution_cost_weight": format(self.execution_cost_weight, "f"),
            "data_quality_weight": format(self.data_quality_weight, "f"),
            "candidate_threshold": format(self.candidate_threshold, "f"),
            "watch_threshold": format(self.watch_threshold, "f"),
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> ScannerScoringConfig:
        defaults = cls()
        try:
            return cls(
                technical_weight=_decimal_or_default(
                    data.get("technical_weight"), defaults.technical_weight
                ),
                context_weight=_decimal_or_default(
                    data.get("context_weight"), defaults.context_weight
                ),
                reward_risk_weight=_decimal_or_default(
                    data.get("reward_risk_weight"), defaults.reward_risk_weight
                ),
                market_risk_weight=_decimal_or_default(
                    data.get("market_risk_weight"), defaults.market_risk_weight
                ),
                execution_cost_weight=_decimal_or_default(
                    data.get("execution_cost_weight"), defaults.execution_cost_weight
                ),
                data_quality_weight=_decimal_or_default(
                    data.get("data_quality_weight"), defaults.data_quality_weight
                ),
                candidate_threshold=_decimal_or_default(
                    data.get("candidate_threshold"), defaults.candidate_threshold
                ),
                watch_threshold=_decimal_or_default(
                    data.get("watch_threshold"), defaults.watch_threshold
                ),
            )
        except ValueError:
            return defaults


@dataclass
class AppConfig:
    environment: IGEnvironment = IGEnvironment.DEMO
    ig_username: str = ""
    ig_password: SecretValue | None = field(default=None, repr=False)
    ig_api_key: SecretValue | None = field(default=None, repr=False)
    selected_account_id: str | None = None
    last_selected_product_epic: str | None = None
    chart_source_overrides: dict[str, str] = field(default_factory=dict)
    product_market_bindings: tuple[IGProductMarketBinding, ...] = ()
    connection_profiles: dict[IGEnvironment, IGConnectionProfileConfig] = field(
        default_factory=dict
    )
    workspace: WorkspaceState = field(default_factory=WorkspaceState)
    scanner_execution_costs: ScannerExecutionCostConfig = field(
        default_factory=ScannerExecutionCostConfig
    )
    scanner_scoring: ScannerScoringConfig = field(default_factory=ScannerScoringConfig)
    scanner_profiles: ScannerProfileCatalog = field(default_factory=ScannerProfileCatalog)
    read_only: bool = True
    enable_live_trading: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.environment, str):
            self.environment = IGEnvironment(self.environment.lower())
        self.chart_source_overrides = _normalize_chart_source_overrides(self.chart_source_overrides)
        self.product_market_bindings = _normalize_product_market_bindings(
            self.product_market_bindings
        )
        self.connection_profiles = _normalize_profiles(
            self.connection_profiles,
            legacy_environment=self.environment,
            legacy_identifier=self.ig_username,
            legacy_account_id=self.selected_account_id,
        )
        if self.enable_live_trading and self.read_only:
            raise ValueError("enable_live_trading cannot be true while read_only is true.")

    def to_file_dict(self) -> dict[str, Any]:
        """Return a safe representation for disk persistence.

        Secrets are intentionally excluded. They must come from a credential store or
        environment variables during P00.
        """

        return {
            "environment": self.environment.value,
            "ig_username": self.ig_username,
            "selected_account_id": self.selected_account_id,
            "last_selected_product_epic": self.last_selected_product_epic,
            "chart_source_overrides": dict(sorted(self.chart_source_overrides.items())),
            "product_market_bindings": [
                {
                    "product_epic": binding.product_epic,
                    "canonical_underlying_id": binding.canonical_underlying_id.value,
                    "reference_epic": binding.reference_epic,
                    "provenance": list(binding.provenance),
                }
                for binding in sorted(
                    self.product_market_bindings,
                    key=lambda item: item.product_epic,
                )
            ],
            "connection_profiles": {
                environment.value: profile.to_file_dict()
                for environment, profile in self.connection_profiles.items()
            },
            "workspace": self.workspace.to_file_dict(),
            "scanner_execution_costs": self.scanner_execution_costs.to_file_dict(),
            "scanner_scoring": self.scanner_scoring.to_file_dict(),
            "scanner_profiles": self.scanner_profiles.to_file_dict(),
            "read_only": self.read_only,
            "enable_live_trading": False,
        }

    @classmethod
    def from_mapping(
        cls,
        data: dict[str, Any],
        *,
        allow_live_trading: bool = False,
    ) -> AppConfig:
        requested_live_trading = bool(data.get("enable_live_trading", False))
        enable_live_trading = requested_live_trading and allow_live_trading
        read_only = bool(data.get("read_only", True))
        if not allow_live_trading:
            read_only = True
        profiles = data.get("connection_profiles", {})
        if not isinstance(profiles, dict):
            profiles = {}
        connection_profiles = {
            IGEnvironment(env): IGConnectionProfileConfig.from_mapping(IGEnvironment(env), value)
            for env, value in profiles.items()
            if env in {item.value for item in IGEnvironment} and isinstance(value, dict)
        }
        workspace_data = data.get("workspace", {})
        workspace = (
            WorkspaceState.from_mapping(workspace_data)
            if isinstance(workspace_data, dict)
            else WorkspaceState()
        )
        scanner_cost_data = data.get("scanner_execution_costs", {})
        scanner_execution_costs = (
            ScannerExecutionCostConfig.from_mapping(scanner_cost_data)
            if isinstance(scanner_cost_data, dict)
            else ScannerExecutionCostConfig()
        )
        scanner_scoring_data = data.get("scanner_scoring", {})
        scanner_scoring = (
            ScannerScoringConfig.from_mapping(scanner_scoring_data)
            if isinstance(scanner_scoring_data, dict)
            else ScannerScoringConfig()
        )
        scanner_profiles_data = data.get("scanner_profiles", {})
        scanner_profiles = ScannerProfileCatalog.from_mapping(scanner_profiles_data)
        return cls(
            environment=IGEnvironment(str(data.get("environment", IGEnvironment.DEMO)).lower()),
            ig_username=str(data.get("ig_username", "")),
            selected_account_id=data.get("selected_account_id") or None,
            last_selected_product_epic=data.get("last_selected_product_epic") or None,
            chart_source_overrides={
                str(key): str(value)
                for key, value in data.get("chart_source_overrides", {}).items()
                if str(key).strip() and str(value).strip()
            }
            if isinstance(data.get("chart_source_overrides", {}), dict)
            else {},
            product_market_bindings=_parse_product_market_bindings(
                data.get("product_market_bindings", ())
            ),
            connection_profiles=connection_profiles,
            workspace=workspace,
            scanner_execution_costs=scanner_execution_costs,
            scanner_scoring=scanner_scoring,
            scanner_profiles=scanner_profiles,
            read_only=read_only,
            enable_live_trading=enable_live_trading,
        )


def load_config(path: Path, *, allow_live_trading: bool = False) -> AppConfig:
    if not path.exists():
        return AppConfig()
    with path.open("r", encoding="utf-8") as config_file:
        data = json.load(config_file)
    if not isinstance(data, dict):
        raise ValueError("Configuration file must contain a JSON object.")
    return AppConfig.from_mapping(data, allow_live_trading=allow_live_trading)


def save_config(config: AppConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as config_file:
            json.dump(config.to_file_dict(), config_file, indent=2, sort_keys=True)
            config_file.write("\n")
            config_file.flush()
            os.fsync(config_file.fileno())
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def default_config_path() -> Path:
    return Path.home() / ".trading_ig_assistant" / "config.json"


def default_paper_database_path() -> Path:
    """Return the local Paper database path without creating any filesystem object."""

    return default_config_path().parent / "data" / "trading_ig_assistant.sqlite"


def _normalize_profiles(
    profiles: dict[IGEnvironment, IGConnectionProfileConfig],
    *,
    legacy_environment: IGEnvironment,
    legacy_identifier: str,
    legacy_account_id: str | None,
) -> dict[IGEnvironment, IGConnectionProfileConfig]:
    normalized: dict[IGEnvironment, IGConnectionProfileConfig] = {}
    for environment in IGEnvironment:
        profile = profiles.get(environment) or profiles.get(environment.value)  # type: ignore[arg-type]
        if profile is None:
            profile = IGConnectionProfileConfig(environment=environment)
        if isinstance(profile, dict):
            profile = IGConnectionProfileConfig.from_mapping(environment, profile)
        normalized[environment] = profile

    if legacy_identifier and not normalized[legacy_environment].identifier:
        normalized[legacy_environment] = IGConnectionProfileConfig(
            environment=legacy_environment,
            identifier=legacy_identifier,
            selected_account_id=legacy_account_id,
        )
    return normalized


def _default_chart_source_overrides() -> dict[str, str]:
    return {
        "IX.D.NASDAQ.OPTCALL2.IP": "IX.D.NASDAQ.IFD.IP",
        "IX.D.NASDAQ.OPTPUT2.IP": "IX.D.NASDAQ.IFD.IP",
    }


def _default_product_market_bindings() -> tuple[IGProductMarketBinding, ...]:
    us_tech_provenance = ("configuration:validated-us-tech-reference-2026-11-05",)
    verified_barrier_provenance = (
        "local-evidence:live-product-discovery-2026-11-06",
        "operator:approved-exact-barrier-pairs-2026-11-06",
    )
    return (
        IGProductMarketBinding(
            product_epic="IX.D.CAC.IMF.IP",
            canonical_underlying_id=CanonicalUnderlyingId.FRANCE_40,
            reference_epic="IX.D.CAC.IMF.IP",
            provenance=("human:demo-cfd-france-40-chart-2026-11-06",),
        ),
        IGProductMarketBinding(
            product_epic="IX.D.NASDAQ.OPTCALL2.IP",
            canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
            reference_epic="IX.D.NASDAQ.IFD.IP",
            provenance=us_tech_provenance,
        ),
        IGProductMarketBinding(
            product_epic="IX.D.NASDAQ.OPTPUT2.IP",
            canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
            reference_epic="IX.D.NASDAQ.IFD.IP",
            provenance=us_tech_provenance,
        ),
        IGProductMarketBinding(
            product_epic="IX.D.CAC.OPTCALL2.IP",
            canonical_underlying_id=CanonicalUnderlyingId.FRANCE_40,
            reference_epic="IX.D.CAC.IMF.IP",
            provenance=verified_barrier_provenance,
        ),
        IGProductMarketBinding(
            product_epic="IX.D.CAC.OPTPUT2.IP",
            canonical_underlying_id=CanonicalUnderlyingId.FRANCE_40,
            reference_epic="IX.D.CAC.IMF.IP",
            provenance=verified_barrier_provenance,
        ),
        IGProductMarketBinding(
            product_epic="IX.D.DAX.OPTCALL.IP",
            canonical_underlying_id=CanonicalUnderlyingId.GERMANY_40,
            reference_epic="IX.D.DAX.IFMM.IP",
            provenance=verified_barrier_provenance,
        ),
        IGProductMarketBinding(
            product_epic="IX.D.DAX.OPTPUT.IP",
            canonical_underlying_id=CanonicalUnderlyingId.GERMANY_40,
            reference_epic="IX.D.DAX.IFMM.IP",
            provenance=verified_barrier_provenance,
        ),
        IGProductMarketBinding(
            product_epic="CC.D.CL.OPTCALL2.IP",
            canonical_underlying_id=CanonicalUnderlyingId.US_CRUDE,
            reference_epic="CC.D.CL.UEF.IP",
            provenance=verified_barrier_provenance,
        ),
        IGProductMarketBinding(
            product_epic="CC.D.CL.OPTPUT2.IP",
            canonical_underlying_id=CanonicalUnderlyingId.US_CRUDE,
            reference_epic="CC.D.CL.UEF.IP",
            provenance=verified_barrier_provenance,
        ),
    )


def _normalize_chart_source_overrides(overrides: dict[str, str] | object) -> dict[str, str]:
    normalized = _default_chart_source_overrides()
    if isinstance(overrides, dict):
        for key, value in overrides.items():
            key_text = str(key).strip()
            value_text = str(value).strip()
            if key_text and value_text:
                normalized[key_text] = value_text
    return normalized


def _normalize_product_market_bindings(
    bindings: tuple[IGProductMarketBinding, ...] | object,
) -> tuple[IGProductMarketBinding, ...]:
    by_product = {binding.product_epic: binding for binding in _default_product_market_bindings()}
    if isinstance(bindings, (tuple, list)):
        supplied_epics: set[str] = set()
        for binding in bindings:
            if not isinstance(binding, IGProductMarketBinding):
                raise ValueError("product market bindings must be typed bindings")
            if binding.product_epic in supplied_epics:
                raise ValueError("product market bindings contain duplicate product EPICs")
            supplied_epics.add(binding.product_epic)
            by_product[binding.product_epic] = binding
    elif bindings:
        raise ValueError("product market bindings must be a sequence")
    return tuple(by_product[key] for key in sorted(by_product))


def _parse_product_market_bindings(data: object) -> tuple[IGProductMarketBinding, ...]:
    if data in (None, ()):
        return ()
    if not isinstance(data, list):
        raise ValueError("product_market_bindings must be a list")
    parsed: list[IGProductMarketBinding] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("product market binding must be an object")
        provenance = item.get("provenance", ())
        if not isinstance(provenance, list) or any(
            not isinstance(value, str) for value in provenance
        ):
            raise ValueError("product market binding provenance must be a text list")
        try:
            canonical = CanonicalUnderlyingId(str(item.get("canonical_underlying_id", "")))
        except ValueError as exc:
            raise ValueError("product market binding canonical underlying is unsupported") from exc
        parsed.append(
            IGProductMarketBinding(
                product_epic=str(item.get("product_epic", "")),
                canonical_underlying_id=canonical,
                reference_epic=str(item.get("reference_epic", "")),
                provenance=tuple(provenance),
            )
        )
    return tuple(parsed)


def _decimal_to_text(value: Decimal | None) -> str | None:
    return format(value, "f") if value is not None else None


def _safe_optional_decimal(value: object) -> Decimal | None:
    if value is None or not str(value).strip():
        return None
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    if not parsed.is_finite() or parsed < 0:
        return None
    return parsed


def _decimal_or_default(value: object, default: Decimal) -> Decimal:
    if value is None or not str(value).strip():
        return default
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return default
    return parsed if parsed.is_finite() else default
