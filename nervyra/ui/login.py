"""Login dialog."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PySide6.QtCore import Qt

from ..paths import app_icon

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nervyra – Login")
        self.setMinimumWidth(360)
        ic = app_icon()
        if not ic.isNull():
            self.setWindowIcon(ic)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Username:"))
        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("e.g., osama")
        lay.addWidget(self.user_edit)

        lay.addWidget(QLabel("Password:"))
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)
        lay.addWidget(self.pass_edit)

        row = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.ok_btn = QPushButton("Login")

        # --- Make Login the default action when pressing Enter ---
        self.ok_btn.setDefault(True)
        self.ok_btn.setAutoDefault(True)
        self.cancel_btn.setAutoDefault(False)

        # Pressing Enter in either field triggers Login
        self.user_edit.returnPressed.connect(self.ok_btn.click)
        self.pass_edit.returnPressed.connect(self.ok_btn.click)

        # Wire up clicks
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self.accept)

        row.addStretch()
        row.addWidget(self.cancel_btn)
        row.addWidget(self.ok_btn)
        lay.addLayout(row)

        # Start focus in the username box
        self.user_edit.setFocus()

    def creds(self) -> tuple[str, str]:
        return self.user_edit.text().strip(), self.pass_edit.text()


# ---------- Admin: Create User dialog ----------
