"""Apply a centralized Qt palette and QSS without touching domain values."""

from __future__ import annotations

from importlib.resources import files

from PyQt5 import QtGui, QtWidgets

from trading_ig_assistant.ui.theme.tokens import DARK_THEME_TOKENS, ThemeTokens


class ThemeManager:
    def __init__(self, tokens: ThemeTokens = DARK_THEME_TOKENS) -> None:
        self._tokens = tokens

    @property
    def tokens(self) -> ThemeTokens:
        return self._tokens

    def stylesheet(self) -> str:
        template = (
            files("trading_ig_assistant.ui.theme")
            .joinpath("tradingig_dark.qss")
            .read_text(encoding="utf-8")
        )
        for placeholder, value in self._tokens.replacements().items():
            template = template.replace(placeholder, value)
        if "@" in template:
            raise ValueError("theme stylesheet contains an unresolved token")
        return template

    def apply(self, application: QtWidgets.QApplication) -> None:
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(self._tokens.background_base))
        palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(self._tokens.text_primary))
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(self._tokens.surface_1))
        palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(self._tokens.surface_2))
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor(self._tokens.text_primary))
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor(self._tokens.surface_1))
        palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(self._tokens.text_primary))
        palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(self._tokens.accent_blue))
        palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#FFFFFF"))
        palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(self._tokens.surface_2))
        palette.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(self._tokens.text_primary))
        palette.setColor(QtGui.QPalette.Link, QtGui.QColor(self._tokens.accent_cyan))
        palette.setColor(
            QtGui.QPalette.Disabled,
            QtGui.QPalette.WindowText,
            QtGui.QColor(self._tokens.semantic_unknown),
        )
        palette.setColor(
            QtGui.QPalette.Disabled,
            QtGui.QPalette.Text,
            QtGui.QColor(self._tokens.semantic_unknown),
        )
        palette.setColor(
            QtGui.QPalette.Disabled,
            QtGui.QPalette.ButtonText,
            QtGui.QColor(self._tokens.semantic_unknown),
        )
        palette.setColor(
            QtGui.QPalette.Disabled,
            QtGui.QPalette.Base,
            QtGui.QColor(self._tokens.surface_2),
        )
        application.setPalette(palette)
        application.setStyleSheet(self.stylesheet())
