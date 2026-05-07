"""Read-only application log viewer."""

from __future__ import annotations

from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from trading_ig_assistant.utils.logging_config import default_log_path

MAX_LOG_CHARS = 250_000


class LogViewDialog(QtWidgets.QDialog):
    def __init__(
        self,
        log_path: Path | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._log_path = log_path or default_log_path()
        self.setWindowTitle("TradingIG Log")
        self.resize(980, 640)
        self._build_ui()
        self._load_log()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        self.path_label = QtWidgets.QLabel(str(self._log_path))
        self.path_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.path_label)

        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        layout.addWidget(self.log_text, stretch=1)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        refresh_button = QtWidgets.QPushButton("Refresh")
        copy_path_button = QtWidgets.QPushButton("Copy Path")
        close_button = QtWidgets.QPushButton("Close")
        refresh_button.clicked.connect(self._load_log)
        copy_path_button.clicked.connect(self._copy_path)
        close_button.clicked.connect(self.close)
        buttons.addWidget(refresh_button)
        buttons.addWidget(copy_path_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def _load_log(self) -> None:
        if not self._log_path.exists():
            self.log_text.setPlainText("Log file does not exist yet.")
            return
        text = self._log_path.read_text(encoding="utf-8", errors="replace")
        if len(text) > MAX_LOG_CHARS:
            text = text[-MAX_LOG_CHARS:]
            text = "[Showing last part of log file]\n" + text
        self.log_text.setPlainText(text)
        self.log_text.moveCursor(QtGui.QTextCursor.End)

    def _copy_path(self) -> None:
        QtWidgets.QApplication.clipboard().setText(str(self._log_path))
