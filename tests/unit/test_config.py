from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.app.config import (
    AppConfig,
    IGConnectionProfileConfig,
    IGEnvironment,
    ScannerExecutionCostConfig,
    ScannerScoringConfig,
    WorkspaceState,
    default_paper_database_path,
    load_config,
    save_config,
)
from trading_ig_assistant.domain.analysis import StrategyId
from trading_ig_assistant.domain.market_navigation import IGProductMarketBinding
from trading_ig_assistant.domain.markets import CanonicalUnderlyingId
from trading_ig_assistant.domain.scanner_profiles import (
    ScannerProfileCatalog,
    ScannerProfilePatch,
)


def test_default_config_is_demo_read_only() -> None:
    config = AppConfig()

    assert config.environment == IGEnvironment.DEMO
    assert config.read_only is True
    assert config.enable_live_trading is False


def test_default_paper_database_path_is_local_and_side_effect_free(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    path = default_paper_database_path()

    assert path == tmp_path / ".trading_ig_assistant" / "data" / "trading_ig_assistant.sqlite"
    assert path.exists() is False


def test_saved_config_excludes_password_and_api_key(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config = AppConfig(
        environment=IGEnvironment.DEMO,
        ig_username="demo-user",
        ig_password=SecretValue("fake-password"),
        ig_api_key=SecretValue("fake-api-key"),
        selected_account_id="SANITIZED_ACCOUNT",
    )

    save_config(config, config_path)

    saved_text = config_path.read_text(encoding="utf-8")
    assert "fake-password" not in saved_text
    assert "fake-api-key" not in saved_text
    assert "ig_password" not in saved_text
    assert "ig_api_key" not in saved_text


def test_config_file_cannot_enable_live_trading_without_explicit_flag(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        """
        {
          "environment": "live",
          "ig_username": "demo-user",
          "read_only": false,
          "enable_live_trading": true
        }
        """,
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.environment == IGEnvironment.LIVE
    assert config.read_only is True
    assert config.enable_live_trading is False


def test_profile_config_saves_non_secret_identifiers_only(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config = AppConfig(
        environment=IGEnvironment.LIVE,
        connection_profiles={
            IGEnvironment.LIVE: IGConnectionProfileConfig(
                environment=IGEnvironment.LIVE,
                identifier="liveuser",
                selected_account_id="LIVE123",
            ),
            IGEnvironment.DEMO: IGConnectionProfileConfig(
                environment=IGEnvironment.DEMO,
                identifier="demouser",
                selected_account_id="DEMO123",
            ),
        },
    )

    save_config(config, config_path)
    saved_text = config_path.read_text(encoding="utf-8")
    loaded = load_config(config_path)

    assert "password" not in saved_text.lower()
    assert "api_key" not in saved_text.lower()
    assert loaded.connection_profiles[IGEnvironment.LIVE].identifier == "liveuser"
    assert loaded.connection_profiles[IGEnvironment.DEMO].selected_account_id == "DEMO123"


def test_config_persists_last_selected_product_epic(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config = AppConfig(
        environment=IGEnvironment.LIVE,
        last_selected_product_epic="IX.D.NASDAQ.IFD.IP",
    )

    save_config(config, config_path)
    loaded = load_config(config_path)

    assert loaded.last_selected_product_epic == "IX.D.NASDAQ.IFD.IP"


def test_config_persists_chart_source_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config = AppConfig(
        environment=IGEnvironment.LIVE,
        chart_source_overrides={"us tech 100": "IX.D.NASDAQ.IFD.IP"},
    )

    save_config(config, config_path)
    loaded = load_config(config_path)

    assert loaded.chart_source_overrides["us tech 100"] == "IX.D.NASDAQ.IFD.IP"
    assert loaded.chart_source_overrides["IX.D.NASDAQ.OPTCALL2.IP"] == "IX.D.NASDAQ.IFD.IP"
    assert loaded.chart_source_overrides["IX.D.NASDAQ.OPTPUT2.IP"] == "IX.D.NASDAQ.IFD.IP"
    assert "US Tech 100" not in loaded.chart_source_overrides


def test_config_persists_typed_product_market_bindings(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    binding = IGProductMarketBinding(
        product_epic="GOLD.BARRIER.CALL",
        canonical_underlying_id=CanonicalUnderlyingId.SPOT_GOLD,
        reference_epic="CS.D.CFEGOLD.CEF.IP",
        provenance=("operator:explicit", "ig:demo-read-only"),
    )

    save_config(AppConfig(product_market_bindings=(binding,)), config_path)
    loaded = load_config(config_path)

    assert binding in loaded.product_market_bindings
    assert all(item.provenance for item in loaded.product_market_bindings)


def test_default_product_bindings_include_verified_products() -> None:
    config = AppConfig()
    by_product = {binding.product_epic: binding for binding in config.product_market_bindings}

    expected = {
        "IX.D.CAC.IMF.IP": (CanonicalUnderlyingId.FRANCE_40, "IX.D.CAC.IMF.IP"),
        "IX.D.NASDAQ.OPTCALL2.IP": (
            CanonicalUnderlyingId.US_TECH_100,
            "IX.D.NASDAQ.IFD.IP",
        ),
        "IX.D.NASDAQ.OPTPUT2.IP": (
            CanonicalUnderlyingId.US_TECH_100,
            "IX.D.NASDAQ.IFD.IP",
        ),
        "IX.D.CAC.OPTCALL2.IP": (CanonicalUnderlyingId.FRANCE_40, "IX.D.CAC.IMF.IP"),
        "IX.D.CAC.OPTPUT2.IP": (CanonicalUnderlyingId.FRANCE_40, "IX.D.CAC.IMF.IP"),
        "IX.D.DAX.OPTCALL.IP": (
            CanonicalUnderlyingId.GERMANY_40,
            "IX.D.DAX.IFMM.IP",
        ),
        "IX.D.DAX.OPTPUT.IP": (
            CanonicalUnderlyingId.GERMANY_40,
            "IX.D.DAX.IFMM.IP",
        ),
        "CC.D.CL.OPTCALL2.IP": (CanonicalUnderlyingId.US_CRUDE, "CC.D.CL.UEF.IP"),
        "CC.D.CL.OPTPUT2.IP": (CanonicalUnderlyingId.US_CRUDE, "CC.D.CL.UEF.IP"),
    }

    assert set(by_product) == set(expected)
    for product_epic, (canonical, reference_epic) in expected.items():
        binding = by_product[product_epic]
        assert binding.canonical_underlying_id is canonical
        assert binding.reference_epic == reference_epic
        assert binding.provenance
    assert not any("CFDGOLD" in product_epic for product_epic in by_product)


def test_config_rejects_unsupported_product_market_binding(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"product_market_bindings": [{"product_epic": "PRODUCT", '
        '"canonical_underlying_id": "GUESSED", "reference_epic": "REFERENCE", '
        '"provenance": ["fixture"]}]}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="canonical underlying"):
        load_config(config_path)


def test_config_persists_validated_workspace_state(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config = AppConfig(
        workspace=WorkspaceState(
            window_width=960,
            window_height=600,
            splitter_sizes=(600, 360),
        )
    )

    save_config(config, config_path)
    loaded = load_config(config_path)

    assert loaded.workspace == config.workspace


def test_scanner_execution_costs_are_unknown_by_default() -> None:
    costs = AppConfig().scanner_execution_costs

    assert costs.fee_for_product_type("cash_or_dfb") is None
    assert costs.fee_for_product_type("barrier") is None
    assert costs.fee_for_product_type("option") is None
    assert costs.fee_for_product_type("unknown") is None


def test_config_persists_scanner_execution_costs_as_exact_decimals(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config = AppConfig(
        scanner_execution_costs=ScannerExecutionCostConfig(
            cash_or_dfb_fee_per_unit_per_side=Decimal("0"),
            barrier_fee_per_unit_per_side=Decimal("0.125"),
            option_fee_per_unit_per_side=Decimal("1.50"),
        )
    )

    save_config(config, config_path)
    loaded = load_config(config_path)

    saved = config_path.read_text(encoding="utf-8")
    assert '"barrier_fee_per_unit_per_side": "0.125"' in saved
    assert loaded.scanner_execution_costs == config.scanner_execution_costs
    assert loaded.scanner_execution_costs.unknown_fee_per_unit_per_side is None


def test_invalid_scanner_execution_cost_from_file_degrades_to_unknown(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"scanner_execution_costs": {'
        '"cash_or_dfb_fee_per_unit_per_side": "-1", '
        '"barrier_fee_per_unit_per_side": "not-a-number"}}',
        encoding="utf-8",
    )

    loaded = load_config(config_path)

    assert loaded.scanner_execution_costs.cash_or_dfb_fee_per_unit_per_side is None
    assert loaded.scanner_execution_costs.barrier_fee_per_unit_per_side is None


def test_scanner_execution_cost_rejects_negative_direct_value() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        ScannerExecutionCostConfig(option_fee_per_unit_per_side=Decimal("-0.01"))


def test_scanner_scoring_defaults_match_prd_and_persist_exactly(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    scoring = ScannerScoringConfig()
    config = AppConfig(scanner_scoring=scoring)

    assert scoring.component_weights() == {
        "technical": Decimal("30"),
        "context": Decimal("15"),
        "reward_risk": Decimal("20"),
        "market_risk": Decimal("15"),
        "execution_cost": Decimal("10"),
        "data_quality": Decimal("10"),
    }
    assert scoring.candidate_threshold == Decimal("75")
    assert scoring.watch_threshold == Decimal("60")

    save_config(config, config_path)
    loaded = load_config(config_path)

    assert loaded.scanner_scoring == scoring


def test_invalid_scanner_scoring_file_falls_back_to_complete_prd_defaults(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"scanner_scoring": {'
        '"technical_weight": "0", "context_weight": "0", '
        '"reward_risk_weight": "0", "market_risk_weight": "0", '
        '"execution_cost_weight": "0", "data_quality_weight": "0", '
        '"candidate_threshold": "50", "watch_threshold": "80"}}',
        encoding="utf-8",
    )

    loaded = load_config(config_path)

    assert loaded.scanner_scoring == ScannerScoringConfig()


def test_scanner_profile_catalog_persists_exact_keys_and_value_types(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    catalog = ScannerProfileCatalog(
        global_patch=ScannerProfilePatch(
            patch_id="global-v1",
            overrides=(
                ("trend_follow.max_extension_atr", Decimal("1.250")),
                ("trend_follow.valid_for", timedelta(minutes=7)),
            ),
        ),
        account_patches=(
            (
                "DEMO-ABC123",
                ScannerProfilePatch(
                    patch_id="account-demo",
                    overrides=(("breakout.level_lookback", 25),),
                ),
            ),
        ),
        strategy_patches=(
            (
                StrategyId.BREAKOUT,
                ScannerProfilePatch(
                    patch_id="breakout-only",
                    overrides=(("enabled_strategies", (StrategyId.BREAKOUT,)),),
                ),
            ),
        ),
        market_patches=(
            (
                CanonicalUnderlyingId.US_TECH_100,
                ScannerProfilePatch(
                    patch_id="nasdaq-rsi",
                    overrides=(("pullback.buy_rsi_range", (Decimal("35"), Decimal("58.5"))),),
                ),
            ),
        ),
    )

    save_config(AppConfig(scanner_profiles=catalog), config_path)
    loaded = load_config(config_path)

    assert loaded.scanner_profiles == catalog
    raw = config_path.read_text(encoding="utf-8")
    assert '"type": "decimal"' in raw
    assert '"type": "duration_seconds"' in raw
    assert '"type": "strategy_ids"' in raw
    assert '"type": "decimal_tuple"' in raw
    assert "fake-password" not in raw


@pytest.mark.parametrize(
    "scanner_profiles",
    (
        {"accounts": []},
        {
            "strategies": {
                "not-a-strategy": {
                    "patch_id": "bad",
                    "overrides": [
                        {
                            "path": "breakout.level_lookback",
                            "value": {"type": "integer", "value": 20},
                        }
                    ],
                }
            }
        },
        {
            "markets": {
                "US_TECH_100": {
                    "patch_id": "bad-decimal",
                    "overrides": [
                        {
                            "path": "breakout.maximum_extension_atr",
                            "value": {"type": "decimal", "value": 2.5},
                        }
                    ],
                }
            }
        },
        {
            "markets": {
                "NASDAQ": {
                    "patch_id": "unknown-market",
                    "overrides": [
                        {
                            "path": "breakout.level_lookback",
                            "value": {"type": "integer", "value": 25},
                        }
                    ],
                }
            }
        },
    ),
)
def test_malformed_scanner_profile_catalog_is_rejected(
    tmp_path: Path,
    scanner_profiles: object,
) -> None:
    import json

    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"scanner_profiles": scanner_profiles}), encoding="utf-8")

    with pytest.raises(ValueError, match="scanner profile"):
        load_config(config_path)


def test_scanner_profile_patch_rejects_unsupported_persisted_value_type() -> None:
    patch = ScannerProfilePatch(
        patch_id="unsupported",
        overrides=(("breakout.level_lookback", True),),
    )

    with pytest.raises(ValueError, match="boolean"):
        patch.to_file_dict()


def test_initial_canonical_underlying_vocabulary_is_exact() -> None:
    assert tuple(item.value for item in CanonicalUnderlyingId) == (
        "US_TECH_100",
        "FRANCE_40",
        "GERMANY_40",
        "SPOT_GOLD",
        "US_CRUDE",
    )


def test_atomic_config_failure_preserves_previous_file(tmp_path: Path, monkeypatch) -> None:
    import trading_ig_assistant.app.config as config_module

    config_path = tmp_path / "config.json"
    save_config(AppConfig(environment=IGEnvironment.DEMO), config_path)
    original = config_path.read_text(encoding="utf-8")

    def fail_replace(_source, _destination) -> None:
        raise OSError("synthetic replace failure")

    monkeypatch.setattr(config_module.os, "replace", fail_replace)

    with pytest.raises(OSError, match="synthetic replace failure"):
        save_config(AppConfig(environment=IGEnvironment.LIVE), config_path)

    assert config_path.read_text(encoding="utf-8") == original
    assert list(tmp_path.glob("*.tmp")) == []
