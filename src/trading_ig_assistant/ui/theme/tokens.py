"""Immutable visual tokens for the TradingIG dark theme."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeTokens:
    background_base: str
    background_sidebar: str
    surface_1: str
    surface_2: str
    surface_hover: str
    border_default: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent_blue: str
    accent_cyan: str
    semantic_profit: str
    semantic_loss: str
    semantic_warning: str
    semantic_unknown: str
    semantic_critical_bg: str
    semantic_strong_profit_bg: str
    semantic_strong_loss_bg: str

    def replacements(self) -> dict[str, str]:
        return {f"@{name.upper()}@": value for name, value in self.__dict__.items()}


DARK_THEME_TOKENS = ThemeTokens(
    background_base="#090F1C",
    background_sidebar="#0C1627",
    surface_1="#101D31",
    surface_2="#16253A",
    surface_hover="#20324A",
    border_default="#2B4057",
    text_primary="#EAF1FB",
    text_secondary="#A8BAD0",
    text_muted="#75899F",
    accent_blue="#2C83F5",
    accent_cyan="#2AC9EC",
    semantic_profit="#28D184",
    semantic_loss="#FF606B",
    semantic_warning="#FFBC53",
    semantic_unknown="#8995A7",
    semantic_critical_bg="#84212D",
    semantic_strong_profit_bg="#116747",
    semantic_strong_loss_bg="#822936",
)
