# make_user_gui.py
import os, sys, json, binascii, hashlib
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QWidget, QCheckBox
)
from PySide6.QtCore import Qt

# === Departments (edit these to your real list) ===
DEPARTMENTS = [
    "Property / Special Risks",
    "Liability",
    "Life / PA & Medical",
    "Financial Lines",
    "PI",
    "Administration",  # <<< ADDED
]

USERS_FILE = "users.json"

# ----- storage helpers -----
def app_dir() -> str:
    # same folder as this script or frozen EXE
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0])))

def users_path() -> str:
    return os.path.join(app_dir(), USERS_FILE)

def load_users() -> dict:
    path = users_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def save_users(users: dict) -> None:
    path = users_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

# ----- crypto -----
def pbkdf2_hash(password: str, salt_hex: str, iterations: int = 150_000) -> str:
    salt = binascii.unhexlify(salt_hex.encode("ascii"))
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return binascii.hexlify(dk).decode("ascii")

def make_user_record(username: str, password: str, department: str) -> tuple[str, dict]:
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 150_000)
    rec = {
        "department": department,
        "salt": binascii.hexlify(salt).decode("ascii"),
        "hash": binascii.hexlify(h).decode("ascii"),
    }
    return username.lower(), rec

# ----- UI -----
class UserCreator(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Nervyra – Create User")
        self.setMinimumWidth(420)
        self.users = load_users()

        root = QVBoxLayout(self)

        # Username
        root.addWidget(QLabel("Username (will be stored in lowercase):"))
        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("e.g., lina")
        root.addWidget(self.user_edit)

        # Password + confirm
        pw_row = QHBoxLayout()
        pw_col = QVBoxLayout()
        pw_col.addWidget(QLabel("Password:"))
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)
        pw_col.addWidget(self.pass_edit)

        pw_col2 = QVBoxLayout()
        pw_col2.addWidget(QLabel("Confirm password:"))
        self.pass2_edit = QLineEdit()
        self.pass2_edit.setEchoMode(QLineEdit.Password)
        pw_col2.addWidget(self.pass2_edit)

        pw_row.addLayout(pw_col)
        pw_row.addLayout(pw_col2)
        root.addLayout(pw_row)

        # Show password checkbox
        show_cb = QCheckBox("Show password")
        def toggle_show(on: bool):
            mode = QLineEdit.Normal if on else QLineEdit.Password
            self.pass_edit.setEchoMode(mode)
            self.pass2_edit.setEchoMode(mode)
        show_cb.toggled.connect(toggle_show)
        root.addWidget(show_cb)

        # Department
        root.addWidget(QLabel("Department:"))
        self.dept_combo = QComboBox()
        self.dept_combo.addItems(DEPARTMENTS)
        root.addWidget(self.dept_combo)

        # Buttons
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save User")
        self.cancel_btn = QPushButton("Close")
        btn_row.addStretch()
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.save_btn)
        root.addLayout(btn_row)

        self.save_btn.clicked.connect(self.save_user)
        self.cancel_btn.clicked.connect(self.close)

    def error(self, msg: str):
        QMessageBox.critical(self, "Error", msg)

    def info(self, msg: str):
        QMessageBox.information(self, "Info", msg)

    def warn(self, msg: str) -> bool:
        return QMessageBox.question(
            self, "Confirm", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) == QMessageBox.Yes

    def save_user(self):
        username = self.user_edit.text().strip().lower()
        pw = self.pass_edit.text()
        pw2 = self.pass2_edit.text()
        dept = self.dept_combo.currentText()

        # Validation
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
        if exists:
            if not self.warn(f"User '{username}' already exists. Overwrite?"):
                return

        key, record = make_user_record(username, pw, dept)
        self.users[key] = record
        try:
            save_users(self.users)
        except Exception as e:
            return self.error(f"Failed to save users.json:\n{e}")

        self.info(f"User '{key}' saved to:\n{users_path()}")
        # Optional: clear inputs for next entry
        self.pass_edit.clear()
        self.pass2_edit.clear()
        self.user_edit.setFocus()

def main():
    # GUI-only: if you prefer no console on double-click, save as .pyw
    app = QApplication(sys.argv)
    w = UserCreator()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
