"""Compact, honest projection of the latest attested market context."""

from __future__ import annotations

from PyQt5 import QtWidgets

from trading_ig_assistant.app.projections.common import Availability
from trading_ig_assistant.app.projections.macro import MacroVM
from trading_ig_assistant.ui.i18n.language_manager import LanguageManager


class MacroCompactBar(QtWidgets.QFrame):
    def __init__(self, language: LanguageManager) -> None:
        super().__init__()
        self.setProperty("role", "panel")
        self._language = language
        self._snapshot: MacroVM | None = None
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 5, 12, 5)
        self.title_label = QtWidgets.QLabel()
        self.value_label = QtWidgets.QLabel()
        self.value_label.setProperty("role", "muted")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label, stretch=1)
        self.retranslate_ui()

    def set_snapshot(self, snapshot: MacroVM) -> None:
        self._snapshot = snapshot
        self._render()

    def retranslate_ui(self) -> None:
        self.title_label.setText(self._language.text("macro.title"))
        self._render()

    def _render(self) -> None:
        snapshot = self._snapshot
        if snapshot is None or (
            snapshot.news_status is not Availability.READY
            and snapshot.ai_status is not Availability.READY
        ):
            self.value_label.setText(self._language.text("macro.empty"))
            self.value_label.setToolTip(self._language.text("macro.empty"))
            return

        if snapshot.ai_status is Availability.READY:
            confidence = (
                f"{snapshot.ai_confidence * 100:.0f}%"
                if snapshot.ai_confidence is not None
                else "N/A"
            )
            self.value_label.setText(
                self._language.text("macro.ribbon.ai_ready").format(
                    bias=(snapshot.ai_directional_bias or "unknown").upper(),
                    risk=(snapshot.ai_event_risk or "unknown").upper(),
                    confidence=confidence,
                    news=len(snapshot.news_rows),
                    providers=snapshot.news_provider_count,
                )
            )
            validity = (
                snapshot.ai_valid_until_utc.strftime("%Y-%m-%d %H:%M UTC")
                if snapshot.ai_valid_until_utc is not None
                else "N/A"
            )
            summary = snapshot.ai_summary or self._language.text("macro.empty")
            self.value_label.setToolTip(
                self._language.text("macro.ribbon.ai_tooltip").format(
                    summary=summary,
                    validity=validity,
                    flags=", ".join(snapshot.ai_risk_flags) or "N/A",
                )
            )
            return

        self.value_label.setText(
            self._language.text("macro.ribbon.news_ready").format(
                news=len(snapshot.news_rows),
                providers=snapshot.news_provider_count,
            )
        )
        collected = (
            snapshot.news_collected_at_utc.strftime("%Y-%m-%d %H:%M UTC")
            if snapshot.news_collected_at_utc is not None
            else "N/A"
        )
        self.value_label.setToolTip(
            self._language.text("macro.ribbon.news_tooltip").format(
                collected=collected,
                reasons=", ".join(snapshot.ai_reason_codes) or "AI_NOT_REQUESTED",
            )
        )
