"""About dialog for Trading IG Assistant."""

from __future__ import annotations

import subprocess
from importlib import metadata

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant import __version__


class AboutDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About TradingIG")
        self.resize(520, 320)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        header = QtWidgets.QHBoxLayout()

        icon = QtWidgets.QLabel("T")
        icon.setAlignment(QtCore.Qt.AlignCenter)
        icon.setFixedSize(64, 64)
        icon.setStyleSheet(
            "QLabel { background: #2374f2; color: white; font-size: 34px; "
            "font-weight: 800; border-radius: 8px; }"
        )
        header.addWidget(icon)

        text = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel(f"TradingIG {application_version()}")
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        description = QtWidgets.QLabel("Assisted read-only trading workstation for IG.")
        description.setWordWrap(True)
        details = QtWidgets.QLabel(
            "Author: Stephane Rey\n"
            "Email: stephane.franck.rey@gmail.com\n"
            "License: Free and open source\n"
            "Created: 2026"
        )
        text.addWidget(title)
        text.addWidget(description)
        text.addWidget(details)
        header.addLayout(text, stretch=1)
        layout.addLayout(header)

        footer = QtWidgets.QLabel(
            "Powered by Python and PyQt5.\n"
            "Built for assisted IG account monitoring, product discovery, and future charting."
        )
        footer.setWordWrap(True)
        layout.addStretch(1)
        layout.addWidget(footer)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        copy_button = QtWidgets.QPushButton("Copy and Close")
        close_button = QtWidgets.QPushButton("Close")
        copy_button.clicked.connect(self._copy_and_close)
        close_button.clicked.connect(self.close)
        buttons.addWidget(copy_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def _copy_and_close(self) -> None:
        QtWidgets.QApplication.clipboard().setText(
            "TradingIG\n"
            f"Version: {application_version()}\n"
            "Author: Stephane Rey <stephane.franck.rey@gmail.com>\n"
            "License: Free and open source\n"
            "Created: 2026"
        )
        self.accept()


def application_version() -> str:
    try:
        package_version = metadata.version("trading-ig-assistant")
    except metadata.PackageNotFoundError:
        package_version = __version__

    git_suffix = _git_short_sha()
    return f"{package_version}+{git_suffix}" if git_suffix else package_version


def _git_short_sha() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    short_sha = result.stdout.strip()
    return short_sha or None
