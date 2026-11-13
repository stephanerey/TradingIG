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


@dataclass
class ApiProviderConfig:
    """Non-secret provider preferences safe for the functional config file."""

    enabled: bool = False
    last_success_at_utc: str | None = None

    def to_file_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "last_success_at_utc": self.last_success_at_utc,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> ApiProviderConfig:
        return cls(
            enabled=bool(data.get("enabled", False)),
            last_success_at_utc=(
                str(data["last_success_at_utc"])
                if data.get("last_success_at_utc")
                else None
            ),
        )


@dataclass(frozen=True)
class MarketIntelligenceConfig:
    """Safe, user-configurable evidence validity windows in hours."""

    breaking_news_hours: int = 6
    macroeconomics_hours: int = 24
    monetary_policy_hours: int = 72
    geopolitics_hours: int = 168

    def __post_init__(self) -> None:
        if any(
            not 1 <= value <= 24 * 30
            for value in (
                self.breaking_news_hours,
                self.macroeconomics_hours,
                self.monetary_policy_hours,
                self.geopolitics_hours,
            )
        ):
            raise ValueError("market intelligence windows must be between 1 and 720 hours")

    def to_file_dict(self) -> dict[str, int]:
        return {
            "breaking_news_hours": self.breaking_news_hours,
            "macroeconomics_hours": self.macroeconomics_hours,
            "monetary_policy_hours": self.monetary_policy_hours,
            "geopolitics_hours": self.geopolitics_hours,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> MarketIntelligenceConfig:
        defaults = cls()
        try:
            return cls(
                breaking_news_hours=int(
                    data.get("breaking_news_hours", defaults.breaking_news_hours)
                ),
                macroeconomics_hours=int(
                    data.get("macroeconomics_hours", defaults.macroeconomics_hours)
                ),
                monetary_policy_hours=int(
                    data.get("monetary_policy_hours", defaults.monetary_policy_hours)
                ),
                geopolitics_hours=int(
                    data.get("geopolitics_hours", defaults.geopolitics_hours)
                ),
            )
        except (TypeError, ValueError):
            return defaults


@dataclass(frozen=True)
class WorkspaceState:
    window_width: int | None = None
    window_height: int | None = None
    splitter_sizes: tuple[int, ...] = ()
    layout_version: int = 1
    window_geometry: str | None = None
    active_page: str = "dashboard"
    active_subtabs: tuple[tuple[str, int], ...] = ()
    sidebar_collapsed: bool = False
    theme: str = "dark"
    locale: str = "fr_FR"

    def __post_init__(self) -> None:
        if self.window_width is not None and self.window_width <= 0:
            raise ValueError("window_width must be positive")
        if self.window_height is not None and self.window_height <= 0:
            raise ValueError("window_height must be positive")
        if any(size < 0 for size in self.splitter_sizes):
            raise ValueError("splitter_sizes must not contain negative values")
        if self.layout_version < 1:
            raise ValueError("layout_version must be positive")
        if not self.active_page.strip():
            raise ValueError("active_page must not be blank")
        if any(not page.strip() or index < 0 for page, index in self.active_subtabs):
            raise ValueError("active_subtabs must contain page names and non-negative indexes")
        if self.theme not in {"dark"}:
            raise ValueError("unsupported workspace theme")
        if self.locale not in {"fr_FR", "en_US"}:
            raise ValueError("unsupported workspace locale")

    def to_file_dict(self) -> dict[str, Any]:
        return {
            "window_width": self.window_width,
            "window_height": self.window_height,
            "splitter_sizes": list(self.splitter_sizes),
            "layout_version": self.layout_version,
            "window_geometry": self.window_geometry,
            "active_page": self.active_page,
            "active_subtabs": dict(self.active_subtabs),
            "sidebar_collapsed": self.sidebar_collapsed,
            "theme": self.theme,
            "locale": self.locale,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> WorkspaceState:
        width = data.get("window_width")
        height = data.get("window_height")
        sizes = data.get("splitter_sizes", [])
        active_subtabs = data.get("active_subtabs", {})
        try:
            parsed_width = int(width) if width is not None else None
            parsed_height = int(height) if height is not None else None
            parsed_sizes = tuple(int(size) for size in sizes) if isinstance(sizes, list) else ()
            parsed_subtabs = (
                tuple(sorted((str(page), int(index)) for page, index in active_subtabs.items()))
                if isinstance(active_subtabs, dict)
                else ()
            )
            return cls(
                window_width=parsed_width,
                window_height=parsed_height,
                splitter_sizes=parsed_sizes,
                layout_version=int(data.get("layout_version", 1)),
                window_geometry=(
                    str(data["window_geometry"])
                    if data.get("window_geometry") is not None
                    else None
                ),
                active_page=str(data.get("active_page", "dashboard")),
                active_subtabs=parsed_subtabs,
                sidebar_collapsed=bool(data.get("sidebar_collapsed", False)),
                theme=str(data.get("theme", "dark")),
                locale=str(data.get("locale", "fr_FR")),
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
    followed_product_epics: dict[str, tuple[str, ...]] = field(default_factory=dict)
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
    api_providers: dict[str, ApiProviderConfig] = field(default_factory=dict)
    market_intelligence: MarketIntelligenceConfig = field(
        default_factory=MarketIntelligenceConfig
    )
    read_only: bool = True
    enable_live_trading: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.environment, str):
            self.environment = IGEnvironment(self.environment.lower())
        self.followed_product_epics = _normalize_followed_product_epics(
            self.followed_product_epics
        )
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
        self.api_providers = {
            str(provider_id).strip().lower(): (
                value
                if isinstance(value, ApiProviderConfig)
                else ApiProviderConfig.from_mapping(value)
            )
            for provider_id, value in self.api_providers.items()
            if str(provider_id).strip() and isinstance(value, (ApiProviderConfig, dict))
        }
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
            "followed_product_epics": {
                key: list(epics)
                for key, epics in sorted(self.followed_product_epics.items())
            },
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
            "api_providers": {
                provider_id: settings.to_file_dict()
                for provider_id, settings in sorted(self.api_providers.items())
            },
            "market_intelligence": self.market_intelligence.to_file_dict(),
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
        api_provider_data = data.get("api_providers", {})
        api_providers = {
            str(provider_id): ApiProviderConfig.from_mapping(settings)
            for provider_id, settings in api_provider_data.items()
            if isinstance(settings, dict)
        } if isinstance(api_provider_data, dict) else {}
        market_intelligence_data = data.get("market_intelligence", {})
        market_intelligence = MarketIntelligenceConfig.from_mapping(
            market_intelligence_data
            if isinstance(market_intelligence_data, dict)
            else {}
        )
        return cls(
            environment=IGEnvironment(str(data.get("environment", IGEnvironment.DEMO)).lower()),
            ig_username=str(data.get("ig_username", "")),
            selected_account_id=data.get("selected_account_id") or None,
            last_selected_product_epic=data.get("last_selected_product_epic") or None,
            followed_product_epics=(
                data.get("followed_product_epics", {})
                if isinstance(data.get("followed_product_epics", {}), dict)
                else {}
            ),
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
            api_providers=api_providers,
            market_intelligence=market_intelligence,
            read_only=read_only,
            enable_live_trading=enable_live_trading,
        )

    def followed_epics_for(
        self,
        environment: IGEnvironment | str,
        account_id: str | None,
    ) -> tuple[str, ...]:
        key = followed_product_scope_key(environment, account_id)
        return () if key is None else self.followed_product_epics.get(key, ())

    def set_followed_epics(
        self,
        environment: IGEnvironment | str,
        account_id: str | None,
        epics: object,
    ) -> tuple[str, ...]:
        key = followed_product_scope_key(environment, account_id)
        if key is None:
            return ()
        normalized = _normalize_epic_sequence(epics)
        if normalized:
            self.followed_product_epics[key] = normalized
        else:
            self.followed_product_epics.pop(key, None)
        return normalized


def followed_product_scope_key(
    environment: IGEnvironment | str,
    account_id: str | None,
) -> str | None:
    """Return the stable non-secret scope used for an exact-product watchlist."""

    normalized_account = str(account_id or "").strip()
    if not normalized_account:
        return None
    normalized_environment = (
        environment.value
        if isinstance(environment, IGEnvironment)
        else IGEnvironment(str(environment).strip().lower()).value
    )
    return f"{normalized_environment}:{normalized_account}"


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


def _normalize_followed_product_epics(
    values: dict[str, object] | object,
) -> dict[str, tuple[str, ...]]:
    if not isinstance(values, dict):
        return {}
    normalized: dict[str, tuple[str, ...]] = {}
    for raw_key, raw_epics in values.items():
        key = str(raw_key).strip()
        if not key or ":" not in key:
            continue
        environment, account_id = key.split(":", 1)
        if environment not in {item.value for item in IGEnvironment} or not account_id.strip():
            continue
        epics = _normalize_epic_sequence(raw_epics)
        if epics:
            normalized[f"{environment}:{account_id.strip()}"] = epics
    return normalized


def _normalize_epic_sequence(values: object) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        return ()
    return tuple(
        dict.fromkeys(
            text
            for value in values
            if (text := str(value).strip())
        )
    )


def _default_product_market_bindings() -> tuple[IGProductMarketBinding, ...]:
    us_tech_provenance = ("configuration:validated-us-tech-reference-2026-11-05",)
    verified_barrier_provenance = (
        "local-evidence:live-product-discovery-2026-11-06",
        "operator:approved-exact-barrier-pairs-2026-11-06",
    )
    verified_gold_barrier_provenance = (
        "local-evidence:live-product-discovery-2026-11-10",
        "operator:selected-exact-live-product-2026-11-10",
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
        IGProductMarketBinding(
            product_epic="CS.D.CFDGOLD.OPTCALL2.IP",
            canonical_underlying_id=CanonicalUnderlyingId.SPOT_GOLD,
            reference_epic="CS.D.CFEGOLD.CEF.IP",
            provenance=verified_gold_barrier_provenance,
        ),
        IGProductMarketBinding(
            product_epic="CS.D.CFDGOLD.OPTPUT2.IP",
            canonical_underlying_id=CanonicalUnderlyingId.SPOT_GOLD,
            reference_epic="CS.D.CFEGOLD.CEF.IP",
            provenance=verified_gold_barrier_provenance,
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
