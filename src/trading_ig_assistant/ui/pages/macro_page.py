"""Honest Macro/AI empty states until licensed providers are configured."""

from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

from trading_ig_assistant.app.projections.common import Availability
from trading_ig_assistant.app.projections.macro import MacroVM
from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
from trading_ig_assistant.ui.shell.page_specs import PAGE_SPEC_BY_KEY


class MacroPage(QtWidgets.QWidget):
    news_refresh_requested = QtCore.pyqtSignal()
    ai_analysis_requested = QtCore.pyqtSignal(str, int, str)

    def __init__(self, language: LanguageManager) -> None:
        super().__init__()
        self._language = language
        self._snapshot: MacroVM | None = None
        self._ai_key_present = False
        self._ai_busy = False
        self._ai_error: str | None = None
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        self.title = QtWidgets.QLabel()
        font = self.title.font()
        font.setPointSize(16)
        font.setBold(True)
        self.title.setFont(font)
        layout.addWidget(self.title)
        self.safety = QtWidgets.QLabel()
        self.safety.setWordWrap(True)
        layout.addWidget(self.safety)
        self.tabs = QtWidgets.QTabWidget()
        self._messages: list[QtWidgets.QLabel] = []
        for index, _key in enumerate(PAGE_SPEC_BY_KEY["macro"].tab_keys):
            panel = QtWidgets.QWidget()
            panel_layout = QtWidgets.QVBoxLayout(panel)
            message = QtWidgets.QLabel()
            message.setAlignment(QtCore.Qt.AlignTop)
            message.setWordWrap(True)
            message.setMinimumWidth(0)
            message.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
            panel_layout.addWidget(message)
            self._messages.append(message)
            if index == 0:
                self.intelligence_summary = QtWidgets.QLabel()
                self.intelligence_summary.setWordWrap(True)
                self.intelligence_summary.setProperty("role", "card")
                panel_layout.addWidget(self.intelligence_summary)
                self.intelligence_status_row = QtWidgets.QHBoxLayout()
                self.tavily_status = QtWidgets.QLabel()
                self.gdelt_status = QtWidgets.QLabel()
                self.quota_status = QtWidgets.QLabel()
                self.freshness_status = QtWidgets.QLabel()
                for status_label in (
                    self.tavily_status,
                    self.gdelt_status,
                    self.quota_status,
                    self.freshness_status,
                ):
                    status_label.setProperty("role", "card")
                    status_label.setWordWrap(True)
                    self.intelligence_status_row.addWidget(status_label, 1)
                panel_layout.addLayout(self.intelligence_status_row)
                self.news_refresh_button = QtWidgets.QPushButton()
                self.news_refresh_button.clicked.connect(self.news_refresh_requested)
                panel_layout.addWidget(self.news_refresh_button)
                self.tavily_highlights_label = QtWidgets.QLabel()
                panel_layout.addWidget(self.tavily_highlights_label)
                self.tavily_highlights = QtWidgets.QListWidget()
                self.tavily_highlights.setWordWrap(True)
                self.tavily_highlights.setMaximumHeight(220)
                panel_layout.addWidget(self.tavily_highlights)
                self.events_label = QtWidgets.QLabel()
                panel_layout.addWidget(self.events_label)
                self.intelligence_table = QtWidgets.QTableWidget(0, 5)
                self.intelligence_table.setEditTriggers(
                    QtWidgets.QAbstractItemView.NoEditTriggers
                )
                self.intelligence_table.setSelectionBehavior(
                    QtWidgets.QAbstractItemView.SelectRows
                )
                self.intelligence_table.horizontalHeader().setStretchLastSection(True)
                panel_layout.addWidget(self.intelligence_table, stretch=1)
                self.sources_label = QtWidgets.QLabel()
                panel_layout.addWidget(self.sources_label)
                self.news_table = QtWidgets.QTableWidget(0, 5)
                self.news_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
                self.news_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
                self.news_table.horizontalHeader().setStretchLastSection(True)
                panel_layout.addWidget(self.news_table, stretch=1)
                self.sources_label.setVisible(False)
                self.news_table.setVisible(False)
                self.raw_sources_toggle = QtWidgets.QToolButton()
                self.raw_sources_toggle.setObjectName("RawSourcesToggle")
                self.raw_sources_toggle.setCheckable(True)
                self.raw_sources_toggle.setToolButtonStyle(
                    QtCore.Qt.ToolButtonTextOnly
                )
                self.raw_sources_toggle.toggled.connect(self._toggle_raw_sources)
                panel_layout.insertWidget(panel_layout.count() - 2, self.raw_sources_toggle)
            elif index == 1:
                self.calendar_details = QtWidgets.QLabel()
                self.calendar_details.setWordWrap(True)
                self.calendar_details.setProperty("role", "card")
                panel_layout.addWidget(self.calendar_details)
                panel_layout.addStretch(1)
            elif index == 2:
                self.context_summary = QtWidgets.QLabel()
                self.context_summary.setWordWrap(True)
                self.context_summary.setProperty("role", "card")
                panel_layout.addWidget(self.context_summary)
                self.context_table = QtWidgets.QTableWidget(0, 2)
                self.context_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
                self.context_table.horizontalHeader().setStretchLastSection(True)
                panel_layout.addWidget(self.context_table)
            elif index == 3:
                form = QtWidgets.QFormLayout()
                self.ai_model = QtWidgets.QComboBox()
                self.ai_model.setEditable(True)
                self.ai_model.addItem("gpt-6-luna")
                self.ai_max_tokens = QtWidgets.QSpinBox()
                self.ai_max_tokens.setRange(1, 2_000)
                self.ai_max_tokens.setValue(1_000)
                self.ai_model_label = QtWidgets.QLabel()
                self.ai_tokens_label = QtWidgets.QLabel()
                form.addRow(self.ai_model_label, self.ai_model)
                form.addRow(self.ai_tokens_label, self.ai_max_tokens)
                panel_layout.addLayout(form)
                self.ai_payload_preview = QtWidgets.QLabel()
                self.ai_payload_preview.setWordWrap(True)
                self.ai_payload_preview.setMinimumWidth(0)
                self.ai_payload_preview.setSizePolicy(
                    QtWidgets.QSizePolicy.Ignored,
                    QtWidgets.QSizePolicy.Preferred,
                )
                self.ai_payload_preview.setProperty("role", "muted")
                panel_layout.addWidget(self.ai_payload_preview)
                self.ai_source_breakdown = QtWidgets.QLabel()
                self.ai_source_breakdown.setWordWrap(True)
                self.ai_source_breakdown.setProperty("role", "card")
                panel_layout.addWidget(self.ai_source_breakdown)
                self.ai_evidence_label = QtWidgets.QLabel()
                panel_layout.addWidget(self.ai_evidence_label)
                self.ai_evidence_table = QtWidgets.QTableWidget(0, 4)
                self.ai_evidence_table.setEditTriggers(
                    QtWidgets.QAbstractItemView.NoEditTriggers
                )
                self.ai_evidence_table.setSelectionBehavior(
                    QtWidgets.QAbstractItemView.SelectRows
                )
                self.ai_evidence_table.setWordWrap(True)
                self.ai_evidence_table.setAlternatingRowColors(True)
                self.ai_evidence_table.setMinimumHeight(160)
                self.ai_evidence_table.verticalHeader().setVisible(False)
                self.ai_evidence_table.verticalHeader().setDefaultSectionSize(62)
                evidence_header = self.ai_evidence_table.horizontalHeader()
                evidence_header.setSectionResizeMode(
                    0, QtWidgets.QHeaderView.ResizeToContents
                )
                evidence_header.setSectionResizeMode(
                    1, QtWidgets.QHeaderView.ResizeToContents
                )
                evidence_header.setSectionResizeMode(
                    2, QtWidgets.QHeaderView.Interactive
                )
                evidence_header.setSectionResizeMode(
                    3, QtWidgets.QHeaderView.Stretch
                )
                self.ai_evidence_table.setColumnWidth(2, 300)
                self.ai_evidence_table.doubleClicked.connect(
                    lambda _index: self._open_selected_ai_source()
                )
                self.ai_open_source = QtWidgets.QToolButton()
                self.ai_open_source.clicked.connect(self._open_selected_ai_source)
                evidence_panel = QtWidgets.QWidget()
                evidence_layout = QtWidgets.QVBoxLayout(evidence_panel)
                evidence_layout.setContentsMargins(0, 0, 0, 0)
                evidence_layout.setSpacing(6)
                evidence_layout.addWidget(self.ai_evidence_table, stretch=1)
                evidence_layout.addWidget(self.ai_open_source)
                self.ai_consent_detail = QtWidgets.QLabel()
                self.ai_consent_detail.setWordWrap(True)
                self.ai_consent_detail.setMinimumWidth(0)
                self.ai_consent_detail.setSizePolicy(
                    QtWidgets.QSizePolicy.Ignored,
                    QtWidgets.QSizePolicy.Preferred,
                )
                self.ai_consent = QtWidgets.QCheckBox()
                self.ai_consent.toggled.connect(self._update_ai_button)
                self.ai_model.currentTextChanged.connect(self._update_ai_button)
                self.ai_max_tokens.valueChanged.connect(lambda _value: self._refresh_ai())
                self.ai_run_button = QtWidgets.QPushButton()
                self.ai_run_button.clicked.connect(self._request_ai_analysis)
                self.ai_details = QtWidgets.QPlainTextEdit()
                self.ai_details.setReadOnly(True)
                self.ai_details.setMinimumHeight(120)
                result_panel = QtWidgets.QWidget()
                result_layout = QtWidgets.QVBoxLayout(result_panel)
                result_layout.setContentsMargins(0, 0, 0, 0)
                result_layout.setSpacing(6)
                result_layout.addWidget(self.ai_consent_detail)
                result_layout.addWidget(self.ai_consent)
                result_layout.addWidget(self.ai_run_button)
                result_layout.addWidget(self.ai_details, stretch=1)
                self.ai_analysis_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
                self.ai_analysis_splitter.setChildrenCollapsible(False)
                self.ai_analysis_splitter.addWidget(evidence_panel)
                self.ai_analysis_splitter.addWidget(result_panel)
                self.ai_analysis_splitter.setStretchFactor(0, 1)
                self.ai_analysis_splitter.setStretchFactor(1, 2)
                self.ai_analysis_splitter.setSizes([260, 340])
                panel_layout.addWidget(self.ai_analysis_splitter, stretch=1)
            else:
                panel_layout.addStretch(1)
            self.tabs.addTab(panel, "")
        layout.addWidget(self.tabs, stretch=1)
        self.retranslate_ui()

    def set_snapshot(self, snapshot: MacroVM) -> None:
        self._snapshot = snapshot
        self._refresh_news()
        self._refresh_ai()

    def set_news_busy(self, busy: bool) -> None:
        self.news_refresh_button.setEnabled(not busy)
        if busy:
            self._messages[0].setText(self._language.text("macro.news_refreshing"))

    def set_ai_key_present(self, present: bool) -> None:
        self._ai_key_present = present
        self._update_ai_button()
        self._refresh_ai()

    def set_ai_busy(self, busy: bool) -> None:
        self._ai_busy = busy
        self.ai_model.setEnabled(not busy)
        self.ai_max_tokens.setEnabled(not busy)
        self.ai_consent.setEnabled(not busy)
        if busy:
            self._messages[3].setText(self._language.text("macro.ai_running"))
        else:
            self._refresh_ai()
        self._update_ai_button()

    def set_ai_error(self, reason: str) -> None:
        self._ai_error = reason
        self._refresh_ai()

    def retranslate_ui(self) -> None:
        self.title.setText(self._language.text("nav.macro"))
        self.safety.setText(self._language.text("macro.ai_safety"))
        for index, key in enumerate(PAGE_SPEC_BY_KEY["macro"].tab_keys):
            self.tabs.setTabText(index, self._language.text(key))
        keys = (
            "macro.news_unavailable",
            "macro.calendar_unavailable",
            "macro.context_unavailable",
            "macro.ai_unavailable",
        )
        for message, key in zip(self._messages, keys, strict=True):
            message.setText(self._language.text(key))
        self.news_refresh_button.setText(self._language.text("macro.news_refresh"))
        self.news_refresh_button.setToolTip(
            self._language.text("macro.news_refresh_tooltip")
        )
        self.events_label.setText(self._language.text("macro.intelligence.events"))
        self.tavily_highlights_label.setText(
            self._language.text("macro.intelligence.tavily_highlights")
        )
        self.sources_label.setText(self._language.text("macro.intelligence.sources"))
        self.raw_sources_toggle.setText(
            self._language.text("macro.intelligence.show_raw")
        )
        self.intelligence_table.setHorizontalHeaderLabels(
            tuple(
                self._language.text(key)
                for key in (
                    "macro.news.published",
                    "macro.news.source",
                    "macro.news.headline",
                    "macro.intelligence.verification",
                    "macro.news.category",
                )
            )
        )
        self.news_table.setHorizontalHeaderLabels(
            tuple(
                self._language.text(key)
                for key in (
                    "macro.news.published",
                    "macro.news.source",
                    "macro.news.headline",
                    "macro.news.category",
                    "macro.news.importance",
                )
            )
        )
        self.context_table.setHorizontalHeaderLabels(
            (
                self._language.text("macro.context.category"),
                self._language.text("macro.context.items"),
            )
        )
        self.ai_consent.setText(self._language.text("macro.ai_consent"))
        self.ai_consent_detail.setText(self._language.text("macro.ai_consent_detail"))
        self.ai_model_label.setText(self._language.text("macro.ai_model"))
        self.ai_tokens_label.setText(self._language.text("macro.ai_tokens"))
        self.ai_run_button.setText(self._language.text("macro.ai_run"))
        self.ai_run_button.setToolTip(self._language.text("macro.ai_run_tooltip"))
        self.ai_open_source.setText(self._language.text("macro.ai_open_source"))
        self.ai_evidence_table.setHorizontalHeaderLabels(
            (
                self._language.text("macro.news.published"),
                self._language.text("macro.news.source"),
                self._language.text("macro.news.headline"),
                self._language.text("macro.ai_excerpt"),
            )
        )
        self._refresh_news()
        self._refresh_ai()

    def _refresh_news(self) -> None:
        snapshot = self._snapshot
        intelligence_rows = () if snapshot is None else snapshot.intelligence_events
        self.intelligence_table.setRowCount(len(intelligence_rows))
        for row_index, row in enumerate(intelligence_rows):
            values = (
                row.published_at_utc.strftime("%Y-%m-%d %H:%M UTC"),
                ", ".join(row.sources),
                row.headline,
                row.verification_status.upper(),
                row.category.upper(),
            )
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setData(QtCore.Qt.UserRole, row.source_urls)
                self.intelligence_table.setItem(row_index, column, item)
        rows = () if snapshot is None else snapshot.news_rows
        self.news_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = (
                row.published_at_utc.strftime("%Y-%m-%d %H:%M UTC"),
                row.source,
                row.headline,
                row.category.upper(),
                row.importance.upper(),
            )
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setData(QtCore.Qt.UserRole, row.source_url)
                self.news_table.setItem(row_index, column, item)
        tavily_rows = tuple(row for row in rows if row.provider_id == "tavily-news")
        self.tavily_highlights.clear()
        self.tavily_highlights_label.setText(
            self._language.text("macro.intelligence.tavily_highlights_count").format(
                count=len(tavily_rows)
            )
        )
        for row in tavily_rows[:10]:
            if row.published_at_utc.time().isoformat() == "00:00:00":
                time_label = (
                    f"{row.published_at_utc:%Y-%m-%d} · "
                    f"{self._language.text('macro.intelligence.time_unknown')}"
                )
            else:
                time_label = row.published_at_utc.strftime("%Y-%m-%d %H:%M UTC")
            self.tavily_highlights.addItem(
                f"{time_label} · {row.headline} — {row.source}"
            )
        if not tavily_rows:
            self.tavily_highlights.addItem(
                self._language.text("macro.intelligence.no_tavily_item")
            )
        if snapshot is None:
            self.tavily_status.setText("Tavily · N/A")
            self.gdelt_status.setText("GDELT · N/A")
            self.quota_status.setText("Quota · N/A")
            self.freshness_status.setText("Fraîcheur · N/A")
            self.intelligence_summary.setText(
                self._language.text("macro.intelligence.not_collected")
            )
        else:
            tavily_key = next(
                (
                    key
                    for code, key in (
                        ("TAVILY_EMPTY", "macro.intelligence.tavily_empty"),
                        ("TAVILY_NETWORK_ERROR", "macro.intelligence.tavily_network"),
                        ("TAVILY_QUOTA_EXHAUSTED", "macro.intelligence.tavily_quota"),
                        ("TAVILY_HTTP_ERROR", "macro.intelligence.tavily_http_error"),
                        ("TAVILY_PROVIDER_ERROR", "macro.intelligence.tavily_provider_error"),
                        ("TAVILY_API_KEY_MISSING", "macro.intelligence.tavily_disabled"),
                    )
                    if code in snapshot.intelligence_reason_codes
                ),
                None,
            )
            self.tavily_status.setText(
                self._language.text(tavily_key)
                if tavily_key is not None
                else f"Tavily · {snapshot.tavily_status.value.upper()}"
            )
            gdelt_key = next(
                (
                    key
                    for code, key in (
                        ("GDELT_RATE_LIMITED", "macro.intelligence.gdelt_limited"),
                        ("GDELT_CIRCUIT_OPEN", "macro.intelligence.gdelt_limited"),
                        ("GDELT_NETWORK_ERROR", "macro.intelligence.gdelt_network"),
                        ("GDELT_HTTP_ERROR", "macro.intelligence.gdelt_http_error"),
                        ("GDELT_EMPTY", "macro.intelligence.gdelt_empty"),
                        ("GDELT_PROVIDER_DISABLED", "macro.intelligence.gdelt_disabled"),
                    )
                    if code in snapshot.intelligence_reason_codes
                ),
                None,
            )
            self.gdelt_status.setText(
                self._language.text(gdelt_key)
                if gdelt_key is not None
                else f"GDELT · {snapshot.gdelt_status.value.upper()}"
            )
            self.quota_status.setText(
                self._language.text("macro.intelligence.quota").format(
                    used=snapshot.tavily_credits_used,
                    limit=snapshot.tavily_monthly_limit,
                    today=snapshot.tavily_credits_today,
                    remaining=snapshot.tavily_credits_remaining,
                )
            )
            self.freshness_status.setText(
                self._language.text("macro.intelligence.freshness").format(
                    status=snapshot.intelligence_status.value.upper()
                )
            )
            self.intelligence_summary.setText(
                self._language.text("macro.intelligence.contribution").format(
                    tavily=snapshot.tavily_news_count,
                    official=snapshot.official_news_count,
                    gdelt=snapshot.gdelt_news_count,
                )
            )
        self._refresh_calendar_and_context()
        if snapshot is None or snapshot.news_provider_count == 0:
            self._messages[0].setText(self._language.text("macro.news_unavailable"))
        elif snapshot.news_status is Availability.READY:
            self._messages[0].setText(
                self._language.text("macro.news_ready").format(
                    count=len(rows),
                    providers=snapshot.news_provider_count,
                    timestamp=snapshot.generated_at_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                )
            )
        else:
            self._messages[0].setText(
                self._language.text("macro.news_failed").format(
                    reasons=", ".join(snapshot.news_reason_codes) or "N/A"
                )
            )

    @QtCore.pyqtSlot()
    def _request_ai_analysis(self) -> None:
        if not self.ai_consent.isChecked():
            return
        model = self.ai_model.currentText().strip()
        if not model:
            return
        self._ai_error = None
        self.ai_analysis_requested.emit(
            model,
            self.ai_max_tokens.value(),
            self._language.locale,
        )
        self.ai_consent.setChecked(False)

    @QtCore.pyqtSlot()
    def _update_ai_button(self) -> None:
        snapshot = self._snapshot
        news_ready = (
            snapshot is not None
            and snapshot.news_status is Availability.READY
            and bool(snapshot.news_rows)
        )
        self.ai_run_button.setEnabled(
            self._ai_key_present
            and news_ready
            and bool(self.ai_model.currentText().strip())
            and self.ai_consent.isChecked()
            and not self._ai_busy
        )

    def _refresh_ai(self) -> None:
        snapshot = self._snapshot
        count = len(snapshot.news_rows) if snapshot is not None else 0
        selected_count = len(snapshot.ai_evidence_rows) if snapshot is not None else 0
        preview_count = snapshot.ai_preview_source_count if snapshot is not None else 0
        input_tokens = (
            snapshot.ai_estimated_input_tokens or snapshot.ai_preview_input_tokens
            if snapshot is not None
            else 0
        )
        extract_credits = (
            snapshot.ai_tavily_extract_credits
            or snapshot.ai_preview_tavily_extract_credits
            if snapshot is not None
            else 0
        )
        estimated_cost = (
            snapshot.ai_estimated_cost_usd or snapshot.ai_preview_estimated_cost_usd
            if snapshot is not None
            else 0.0
        )
        self.ai_payload_preview.setText(
            self._language.text("macro.ai_payload_preview").format(
                count=selected_count or preview_count or min(count, 5),
                tokens=self.ai_max_tokens.value(),
                input_tokens=input_tokens,
                cost=estimated_cost,
                extract_credits=extract_credits,
            )
        )
        evidence_rows = () if snapshot is None else snapshot.ai_evidence_rows
        analysis_available = (
            snapshot is not None and snapshot.ai_status is Availability.READY
        )
        self.ai_evidence_label.setText(
            self._language.text(
                "macro.ai_evidence_used"
                if analysis_available
                else "macro.ai_evidence_selected"
            )
        )
        self.ai_evidence_table.setRowCount(len(evidence_rows))
        for row_index, row in enumerate(evidence_rows):
            values = (
                row.published_at_utc.strftime("%Y-%m-%d %H:%M UTC"),
                row.source,
                row.headline,
                row.excerpt or self._language.text("macro.ai_excerpt_unavailable"),
            )
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setData(QtCore.Qt.UserRole, row.source_url)
                item.setToolTip(value)
                self.ai_evidence_table.setItem(row_index, column, item)
            self.ai_evidence_table.setRowHeight(row_index, 62)
        self.ai_open_source.setEnabled(bool(evidence_rows))
        if snapshot is None:
            self.ai_source_breakdown.setText(
                self._language.text("macro.ai_source_breakdown_empty")
            )
        else:
            self.ai_source_breakdown.setText(
                self._language.text("macro.ai_source_breakdown").format(
                    total=count,
                    tavily=min(snapshot.tavily_news_count, 20),
                    official=min(snapshot.official_news_count, 20),
                    gdelt=min(snapshot.gdelt_news_count, 20),
                )
            )
        if not self._ai_key_present:
            self._messages[3].setText(self._language.text("macro.ai_key_missing"))
            self.ai_details.setPlainText(self._language.text("macro.ai_result_not_run"))
        elif snapshot is None or snapshot.news_status is not Availability.READY:
            self._messages[3].setText(self._language.text("macro.ai_news_required"))
            self.ai_details.setPlainText(self._language.text("macro.ai_result_not_run"))
        elif snapshot.ai_status is Availability.READY:
            confidence = (
                f"{snapshot.ai_confidence * 100:.1f}%"
                if snapshot.ai_confidence is not None
                else "N/A"
            )
            self._messages[3].setText(
                self._language.text("macro.ai_ready").format(
                    model=snapshot.ai_model_id or "N/A",
                    timestamp=(
                        snapshot.ai_generated_at_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
                        if snapshot.ai_generated_at_utc is not None
                        else "N/A"
                    ),
                )
            )
            self.ai_details.setPlainText(
                self._language.text("macro.ai_result").format(
                    summary=snapshot.ai_summary or "N/A",
                    bias=(snapshot.ai_directional_bias or "unknown").upper(),
                    risk=(snapshot.ai_event_risk or "unknown").upper(),
                    confidence=confidence,
                    flags=", ".join(snapshot.ai_risk_flags) or "N/A",
                    sources=self._format_ai_sources(snapshot),
                    validity=(
                        snapshot.ai_valid_until_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
                        if snapshot.ai_valid_until_utc is not None
                        else "N/A"
                    ),
                )
            )
            if (
                snapshot.ai_generated_at_utc is not None
                and snapshot.news_collected_at_utc is not None
                and snapshot.ai_generated_at_utc < snapshot.news_collected_at_utc
            ):
                self._messages[3].setText(
                    self._messages[3].text()
                    + "\n"
                    + self._language.text("macro.ai_outdated_for_collection")
                )
        elif snapshot.ai_generated_at_utc is not None:
            reasons = ", ".join(snapshot.ai_reason_codes) or "AI_PROVIDER_ERROR"
            self._messages[3].setText(
                self._language.text("macro.ai_attempt_unavailable").format(
                    timestamp=snapshot.ai_generated_at_utc.strftime(
                        "%Y-%m-%d %H:%M:%S UTC"
                    ),
                    reasons=reasons,
                )
            )
            self.ai_details.setPlainText(
                self._language.text("macro.ai_unavailable_result").format(
                    reasons=reasons,
                )
            )
        elif self._ai_error is not None:
            self._messages[3].setText(self._language.text(self._ai_error))
            self.ai_details.setPlainText(
                self._language.text("macro.ai_failed_retry")
            )
        else:
            self._messages[3].setText(self._language.text("macro.ai_ready_to_run"))
            self.ai_details.setPlainText(self._language.text("macro.ai_result_not_run"))
        self._update_ai_button()

    def _format_ai_sources(self, snapshot: MacroVM) -> str:
        rows_by_signal = {
            f"news:{row.item_id}": row
            for row in snapshot.news_rows
        }
        provider_labels = {
            "tavily-news": "Tavily",
            "gdelt-doc": "GDELT",
        }
        citations: list[str] = []
        for signal_id in snapshot.ai_source_signal_ids:
            row = rows_by_signal.get(signal_id)
            if row is None:
                citations.append(f"• {signal_id}")
                continue
            provider = provider_labels.get(
                row.provider_id,
                self._language.text("macro.ai_provider_official"),
            )
            citations.append(
                self._language.text("macro.ai_source_citation").format(
                    provider=provider,
                    headline=row.headline,
                    source=row.source,
                )
            )
        return "\n".join(citations) or "N/A"

    @QtCore.pyqtSlot()
    def _open_selected_ai_source(self) -> None:
        row = self.ai_evidence_table.currentRow()
        if row < 0 and self.ai_evidence_table.rowCount():
            row = 0
        item = self.ai_evidence_table.item(row, 0) if row >= 0 else None
        url = item.data(QtCore.Qt.UserRole) if item is not None else None
        if isinstance(url, str) and url.startswith("https://"):
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    @QtCore.pyqtSlot(bool)
    def _toggle_raw_sources(self, visible: bool) -> None:
        self.sources_label.setVisible(visible)
        self.news_table.setVisible(visible)
        self.raw_sources_toggle.setText(
            self._language.text(
                "macro.intelligence.hide_raw"
                if visible
                else "macro.intelligence.show_raw"
            )
        )

    def _refresh_calendar_and_context(self) -> None:
        snapshot = self._snapshot
        self.calendar_details.setText(
            self._language.text("macro.calendar_explanation")
        )
        counts = () if snapshot is None else snapshot.category_counts
        self.context_table.setRowCount(len(counts))
        for row_index, (category, count) in enumerate(counts):
            self.context_table.setItem(
                row_index,
                0,
                QtWidgets.QTableWidgetItem(category.upper()),
            )
            self.context_table.setItem(
                row_index,
                1,
                QtWidgets.QTableWidgetItem(str(count)),
            )
        if snapshot is None or not counts:
            self.context_summary.setText(
                self._language.text("macro.context_unavailable")
            )
            return
        self._messages[2].setText(
            self._language.text("macro.context_observed")
        )
        self.context_summary.setText(
            self._language.text("macro.context_coverage").format(
                total=len(snapshot.news_rows),
                providers=snapshot.news_provider_count,
                freshness=snapshot.intelligence_status.value.upper(),
            )
        )
