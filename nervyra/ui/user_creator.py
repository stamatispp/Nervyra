"""Admin-only user creation dialog."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QWidget, QComboBox
)
from PySide6.QtCore import Qt

from ..paths import app_icon
from ..auth import load_users, save_users, make_user_record
from ..config import DEPARTMENTS
from ..paths import users_path

class UserCreator(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Nervyra – Create User")
        self.setMinimumWidth(420)
        self.users = load_users()
        root = QVBoxLayout(self)

        root.addWidget(QLabel("Username (stored in lowercase):"))
        self.user_edit = QLineEdit(); self.user_edit.setPlaceholderText("e.g., lina")
        root.addWidget(self.user_edit)

        pw_row = QHBoxLayout()
        col1 = QVBoxLayout(); col2 = QVBoxLayout()
        col1.addWidget(QLabel("Password:"))
        self.pass_edit = QLineEdit(); self.pass_edit.setEchoMode(QLineEdit.Password)
        col1.addWidget(self.pass_edit)
        col2.addWidget(QLabel("Confirm password:"))
        self.pass2_edit = QLineEdit(); self.pass2_edit.setEchoMode(QLineEdit.Password)
        col2.addWidget(self.pass2_edit)
        pw_row.addLayout(col1); pw_row.addLayout(col2); root.addLayout(pw_row)

        show_cb = QCheckBox("Show password")
        show_cb.toggled.connect(
            lambda on: [w.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)
                        for w in (self.pass_edit, self.pass2_edit)]
        )
        root.addWidget(show_cb)

        root.addWidget(QLabel("Department:"))
        self.dept_combo = QComboBox()
        self.dept_combo.addItems(DEPARTMENTS)
        root.addWidget(self.dept_combo)

        # --- Buttons ---
        btn_row = QHBoxLayout()
        self.cancel_btn = QPushButton("Close")
        self.save_btn = QPushButton("Save User")

        # Make "Save User" the default action (Enter will trigger this)
        self.save_btn.setDefault(True)
        self.save_btn.setAutoDefault(True)
        self.cancel_btn.setAutoDefault(False)

        btn_row.addStretch()
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.save_btn)
        root.addLayout(btn_row)

        # Wire up clicks
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self.save_user)

        # Pressing Enter in any text field triggers "Save User"
        self.user_edit.returnPressed.connect(self.save_btn.click)
        self.pass_edit.returnPressed.connect(self.save_btn.click)
        self.pass2_edit.returnPressed.connect(self.save_btn.click)

        # Initial focus
        self.user_edit.setFocus()

    def error(self, msg: str): QMessageBox.critical(self, "Error", msg)
    def info(self, msg: str): QMessageBox.information(self, "Info", msg)
    def warn(self, msg: str) -> bool:
        return QMessageBox.question(
            self, "Confirm", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) == QMessageBox.Yes

    def save_user(self):
        username = self.user_edit.text().strip().lower()
        pw, pw2 = self.pass_edit.text(), self.pass2_edit.text()
        dept = self.dept_combo.currentText()

        if not username:
            return self.error("Please enter a username.")
        if " " in username:
            return self.error("Username cannot contain spaces.")
        if not pw:
            return self.error("Please enter a password.")
        if pw != pw2:
            return self.error("Passwords do not match.")
        if len(pw) < 6:
            return self.error("Password should be at least 6 characters.")
        if dept not in DEPARTMENTS:
            return self.error("Please choose a valid department.")

        exists = username in self.users
        if exists and not self.warn(f"User '{username}' exists. Overwrite?"):
            return

        key, record = make_user_record(username, pw, dept)
        self.users[key] = record
        try:
            save_users(self.users)
        except Exception as e:
            return self.error(f"Failed to save users.json:\n{e}")

        self.users = load_users()  # refresh from disk

        self.info(f"User '{key}' saved.\n{users_path()}")
        self.user_edit.clear()
        self.pass_edit.clear()
        self.pass2_edit.clear()
        self.user_edit.setFocus()


# ---------- Tiny admin header helper ----------
