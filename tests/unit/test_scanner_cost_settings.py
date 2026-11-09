from decimal import Decimal

from PyQt5 import QtWidgets

from trading_ig_assistant.app.config import (
    AppConfig,
    ScannerExecutionCostConfig,
    ScannerScoringConfig,
)
from trading_ig_assistant.domain.market_navigation import IGProductMarketBinding
from trading_ig_assistant.domain.markets import CanonicalUnderlyingId
from trading_ig_assistant.domain.scanner_profiles import (
    ScannerProfileCatalog,
    ScannerProfilePatch,
)
from trading_ig_assistant.ui.settings_dialog import (
    ScannerExecutionCostSettingsWidget,
    ScannerScoringSettingsWidget,
    SettingsDialog,
)


def test_scanner_cost_settings_keep_blank_distinct_from_explicit_zero() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    widget = ScannerExecutionCostSettingsWidget(
        ScannerExecutionCostConfig(defaults_initialized=True)
    )

    assert widget.config().barrier_fee_per_unit_per_side is None

    widget.barrier_fee.setText("0")
    widget.option_fee.setText("1,25")
    config = widget.config()

    assert config.barrier_fee_per_unit_per_side == Decimal("0")
    assert config.option_fee_per_unit_per_side == Decimal("1.25")
    widget.close()
    app.processEvents()


def test_scanner_cost_settings_offer_sourced_indicative_defaults_once() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    widget = ScannerExecutionCostSettingsWidget(ScannerExecutionCostConfig())

    assert widget.cash_or_dfb_fee.text() == "0"
    assert widget.barrier_fee.text() == "0.1"
    assert widget.option_fee.text() == "0.1"
    assert widget.unknown_fee.text() == ""
    assert widget.config().defaults_initialized is True

    widget.barrier_fee.clear()
    explicit_blank = widget.config()
    reopened = ScannerExecutionCostSettingsWidget(explicit_blank)
    assert reopened.barrier_fee.text() == ""
    reopened.restore_indicative_button.click()
    assert reopened.barrier_fee.text() == "0.1"
    widget.close()
    reopened.close()
    app.processEvents()


def test_settings_dialog_preserves_existing_config_and_applies_scanner_costs() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    profiles = ScannerProfileCatalog(
        global_patch=ScannerProfilePatch(
            patch_id="global",
            overrides=(("breakout.level_lookback", 25),),
        )
    )
    binding = IGProductMarketBinding(
        product_epic="GOLD.BARRIER.CALL",
        canonical_underlying_id=CanonicalUnderlyingId.SPOT_GOLD,
        reference_epic="CS.D.CFEGOLD.CEF.IP",
        provenance=("operator:explicit",),
    )
    original = AppConfig(
        last_selected_product_epic="IX.D.TEST.IFD.IP",
        chart_source_overrides={"test": "IX.D.TEST.IFD.IP"},
        product_market_bindings=(binding,),
        scanner_profiles=profiles,
    )
    dialog = SettingsDialog(original, None)
    dialog.scanner_cost_settings.cash_or_dfb_fee.setText("0.40")
    dialog.scanner_cost_settings.barrier_fee.setText("")

    updated = dialog.updated_config()

    assert updated.last_selected_product_epic == "IX.D.TEST.IFD.IP"
    assert updated.chart_source_overrides["test"] == "IX.D.TEST.IFD.IP"
    assert binding in updated.product_market_bindings
    assert updated.scanner_profiles == profiles
    assert updated.scanner_execution_costs.cash_or_dfb_fee_per_unit_per_side == Decimal("0.40")
    assert updated.scanner_execution_costs.barrier_fee_per_unit_per_side is None
    dialog.close()
    app.processEvents()


def test_settings_dialog_rejects_negative_scanner_cost_without_emitting_config() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    dialog = SettingsDialog(AppConfig(), None)
    dialog.scanner_cost_settings.option_fee.setText("-1")
    emitted = []
    dialog.config_applied.connect(emitted.append)

    applied = dialog.apply()

    assert applied is False
    assert emitted == []
    assert "Configuration invalide" in dialog.status.text()
    dialog.close()
    app.processEvents()


def test_scanner_scoring_settings_expose_prd_defaults_and_accept_comma_decimals() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    widget = ScannerScoringSettingsWidget(ScannerScoringConfig())

    assert widget.technical_weight.text() == "30"
    assert widget.candidate_threshold.text() == "75"
    widget.context_weight.setText("12,5")
    widget.watch_threshold.setText("62,5")

    config = widget.config()

    assert config.context_weight == Decimal("12.5")
    assert config.watch_threshold == Decimal("62.5")
    widget.close()
    app.processEvents()


def test_scanner_scoring_settings_reject_inverted_thresholds() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    dialog = SettingsDialog(AppConfig(), None)
    dialog.scanner_scoring_settings.candidate_threshold.setText("50")
    dialog.scanner_scoring_settings.watch_threshold.setText("60")
    emitted = []
    dialog.config_applied.connect(emitted.append)

    applied = dialog.apply()

    assert applied is False
    assert emitted == []
    assert "0 <= watch <= candidate <= 100" in dialog.status.text()
    dialog.close()
    app.processEvents()
