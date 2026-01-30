"""Optional admin header widget (shows current user + Create User button)."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QDialog

from ..state import CURRENT_USER
from .user_creator import UserCreator


def maybe_admin_header(parent_dialog: QDialog) -> QWidget | None:
    """If current user is admin, return a header widget with 'Create User' button (right-aligned)."""
    if not CURRENT_USER.get("is_admin"):
        return None
    header = QWidget(parent_dialog)
    h = QHBoxLayout(header); h.setContentsMargins(0, 0, 0, 0)
    h.addWidget(QLabel(f"<b>User:</b> {CURRENT_USER.get('username','')} &nbsp; "
                       f"<b>Dept:</b> {CURRENT_USER.get('department','')}"))
    h.addStretch()
    btn = QPushButton("Create User")
    btn.setToolTip("Add a new Nervyra user (admins only)")
    btn.clicked.connect(lambda: UserCreator(parent_dialog).exec())
    h.addWidget(btn)
    return header


