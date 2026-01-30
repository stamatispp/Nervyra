from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
    QMessageBox,
    QGridLayout,
)

from ..tools.base import Tool
from ..updater import check_for_updates, open_releases_page
from ..logging_utils import app_data_dir

log = logging.getLogger(__name__)

class DashboardDialog(QDialog):
    def __init__(self, tools: list[Tool], context: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nervyra - Dashboard")
        self.setMinimumSize(900, 600)

        self._tools = tools
        self._context = context
        self._selected_tool: Tool | None = None

        root = QVBoxLayout(self)

        # Header
        header = QHBoxLayout()
        user = context.get("username") or "User"
        dept = context.get("department") or ""
        lbl = QLabel(f"<b>Welcome, {user}</b>  <span style='color:#666'>({dept})</span>")
        lbl.setTextFormat(Qt.RichText)

        header.addWidget(lbl)
        header.addStretch(1)

        btn_updates = QPushButton("Check updates")
        btn_updates.clicked.connect(self._on_check_updates)

        btn_logs = QPushButton("Open logs")
        btn_logs.clicked.connect(self._on_open_logs)

        btn_logout = QPushButton("Logout")
        btn_logout.clicked.connect(self._on_logout)

        header.addWidget(btn_updates)
        header.addWidget(btn_logs)
        header.addWidget(btn_logout)
        root.addLayout(header)

        # Tools grid in scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(12)

        filtered = self._filter_tools(tools, context)
        if not filtered:
            empty = QLabel("No tools are available for your profile.")
            empty.setAlignment(Qt.AlignCenter)
            root.addWidget(empty)
        else:
            cols = 3
            for idx, tool in enumerate(filtered):
                r = idx // cols
                c = idx % cols
                grid.addWidget(self._tool_card(tool), r, c)
            scroll.setWidget(container)
            root.addWidget(scroll, 1)

        # Footer hint
        hint = QLabel("Tip: drop new tools into the <b>plugins</b> folder (each tool has a manifest.json).")
        hint.setTextFormat(Qt.RichText)
        hint.setStyleSheet("color:#666;")
        root.addWidget(hint)

    def selected_tool(self) -> Tool | None:
        return self._selected_tool

    def _filter_tools(self, tools: list[Tool], context: dict) -> list[Tool]:
        dept = context.get("department")
        is_admin = bool(context.get("is_admin"))
        out: list[Tool] = []
        for t in tools:
            if t.admin_only and not is_admin:
                continue
            if t.allowed_departments and dept not in t.allowed_departments:
                continue
            if t.entrypoint is None:
                continue
            out.append(t)
        return out

    def _tool_card(self, tool: Tool) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)

        title = QLabel(f"<b>{tool.name}</b>")
        title.setTextFormat(Qt.RichText)
        desc = QLabel(tool.description or "")
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#555;")

        btn = QPushButton("Open")
        btn.clicked.connect(lambda: self._launch(tool))

        lay.addWidget(title)
        lay.addWidget(desc, 1)
        lay.addWidget(btn)

        w.setStyleSheet(
            "QWidget { background: white; border: 1px solid #ddd; border-radius: 10px; }"
            "QPushButton { padding: 6px 10px; }"
        )
        return w

    def _launch(self, tool: Tool) -> None:
        self._selected_tool = tool
        self.accept()

    def _on_logout(self) -> None:
        self._selected_tool = None
        self.reject()

    def _on_open_logs(self) -> None:
        d = app_data_dir("Nervyra") / "logs"
        d.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))

    def _on_check_updates(self) -> None:
        try:
            info = check_for_updates()
            if not info.get("update_available"):
                QMessageBox.information(self, "Nervyra", "You are on the latest version.")
                return

            latest = info.get("latest_version", "unknown")
            notes = info.get("release_notes", "")
            mb = QMessageBox(self)
            mb.setIcon(QMessageBox.Information)
            mb.setWindowTitle("Update available")
            mb.setText(f"A new version is available: <b>{latest}</b>")
            mb.setInformativeText("Open the downloads page?")
            mb.setDetailedText(notes or "")
            mb.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            if mb.exec() == QMessageBox.Yes:
                open_releases_page()
        except Exception as e:
            log.exception("Update check failed: %s", e)
            QMessageBox.warning(self, "Nervyra", "Could not check for updates right now.")
