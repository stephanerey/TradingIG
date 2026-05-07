"""Macro context ribbon placeholder."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from PyQt5 import QtWidgets


class MacroStatus(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    GREY = "grey"


@dataclass(frozen=True)
class MacroStatusChip:
    label: str
    status: MacroStatus = MacroStatus.GREY


DEFAULT_MACRO_CHIPS = [
    MacroStatusChip("Global regime"),
    MacroStatusChip("FED/FOMC"),
    MacroStatusChip("Macro data"),
    MacroStatusChip("US yields"),
    MacroStatusChip("USD"),
    MacroStatusChip("Oil/Energy"),
    MacroStatusChip("VIX/Volatility"),
    MacroStatusChip("Geopolitical risk"),
    MacroStatusChip("Gold context"),
    MacroStatusChip("Data health"),
]

STATUS_COLORS = {
    MacroStatus.GREEN: ("#0f7b45", "#e5f6ed"),
    MacroStatus.YELLOW: ("#a26500", "#fff3cd"),
    MacroStatus.RED: ("#a61b1b", "#fde7e7"),
    MacroStatus.GREY: ("#4f5965", "#eef1f4"),
}


class MacroRibbonWidget(QtWidgets.QWidget):
    def __init__(
        self,
        chips: list[MacroStatusChip] | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._chips = chips or DEFAULT_MACRO_CHIPS
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        for chip in self._chips:
            layout.addWidget(self._build_chip(chip))
        layout.addStretch(1)

    def _build_chip(self, chip: MacroStatusChip) -> QtWidgets.QLabel:
        foreground, background = STATUS_COLORS[chip.status]
        label = QtWidgets.QLabel(f"{chip.label}: {chip.status.name}")
        label.setStyleSheet(
            "QLabel {"
            f"color: {foreground};"
            f"background: {background};"
            "border-radius: 10px;"
            "padding: 4px 9px;"
            "font-weight: 600;"
            "}"
        )
        return label
