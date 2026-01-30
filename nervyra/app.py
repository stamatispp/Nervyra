"""Application entry logic (Qt event loop + workflow)."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication, QMessageBox, QDialog

from .paths import set_appusermodel_id, app_icon
from .auth import load_users, verify_login
from .config import DEPARTMENTS
from .state import CURRENT_USER
from .ui.login import LoginDialog
from .ui.dashboard import DashboardDialog
from .tools import discover_tools
from .logging_utils import configure_logging, install_crash_handler

log = logging.getLogger(__name__)

def main():
    set_appusermodel_id("Nervyra.App")

    # Qt app
    app = QApplication(sys.argv)
    app.setApplicationName("Nervyra")

    ic = app_icon()
    if not ic.isNull():
        app.setWindowIcon(ic)

    # Logging + crash handler
    configure_logging("Nervyra")
    install_crash_handler("Nervyra")
    log.info("Starting Nervyra %s", __import__("nervyra").__version__)

    # Discover tools once at startup (plugins folder)
    tools = discover_tools()
    if not tools:
        log.warning("No tools discovered. Ensure plugins folder contains manifests.")

    while True:
        # Always reload the latest users.json before each login
        users = load_users()

        # ----- Login -----
        login = LoginDialog()
        if not login.exec():
            return

        username, password = login.creds()
        ok, department, is_admin = verify_login(users, username, password)

        if not ok:
            QMessageBox.critical(None, "Login failed", "Invalid username or password.")
            continue

        if department not in DEPARTMENTS:
            QMessageBox.critical(None, "Login failed",
                                 f"User department '{department}' is not configured.")
            continue

        CURRENT_USER.update({"username": username, "department": department, "is_admin": is_admin})
        log.info("Login success: %s (%s) admin=%s", username, department, is_admin)

        # ======= DASHBOARD LOOP (stay logged in until Logout) =======
        while True:
            ctx = dict(CURRENT_USER)
            dash = DashboardDialog(tools, ctx)
            res = dash.exec()

            if res != QDialog.Accepted:
                # Logout
                log.info("Logout: %s", username)
                CURRENT_USER.update({"username": None, "department": None, "is_admin": False})
                break

            tool = dash.selected_tool()
            if not tool or not tool.entrypoint:
                continue

            log.info("Launching tool: %s (%s)", tool.name, tool.id)
            try:
                tool.entrypoint(ctx)
            except Exception as e:
                log.exception("Tool crashed: %s", e)
                QMessageBox.critical(None, "Nervyra", f"Tool '{tool.name}' crashed. Check logs for details.")

        # end dashboard loop → back to login
