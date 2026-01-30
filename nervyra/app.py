"""Application entry logic (Qt event loop + workflow)."""

from __future__ import annotations

import json
import sys

from PySide6.QtWidgets import QApplication, QMessageBox, QDialog

from .paths import set_appusermodel_id, app_icon, clause_json_path
from .auth import load_users, verify_login
from .config import DEPARTMENTS, REINSURERS_BY_DEPT
from .state import CURRENT_USER
from .ui.login import LoginDialog
from .ui.dialogs import ReinsurerSelectorDialog, InfoInputDialog, ComparisonDialog, FinalReviewDialog, AdminConsole
from .clause_engine import best_unique_matches, is_lm7_line


def main():
    set_appusermodel_id("Nervyra.ClauseChecker")
    app = QApplication(sys.argv)
    app.setApplicationName("Nervyra")
    ic = app_icon()
    if not ic.isNull():
        app.setWindowIcon(ic)

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

        # Set current user context for admin header usage
        CURRENT_USER.update({"username": username, "department": department, "is_admin": is_admin})

        # Admins (Administration dept) → Admin Console
        reinsurers = REINSURERS_BY_DEPT.get(department, [])
        if not reinsurers:
            AdminConsole().exec()
            # After closing admin console, back to login (loop reloads users.json)
            CURRENT_USER.update({"username": None, "department": None, "is_admin": False})
            continue

        # ======= SESSION LOOP (stay logged in until explicit Logout) =======
        while True:
            # ----- Reinsurer selection -----
            sel = ReinsurerSelectorDialog(department, reinsurers, allow_logout=True)
            sel_result = sel.exec()
            if sel_result != QDialog.Accepted:
                # Explicit Logout
                CURRENT_USER.update({"username": None, "department": None, "is_admin": False})
                break  # break session loop → back to login

            reinsurer = sel.selected()

            # Verify data path
            jpath = clause_json_path(department, reinsurer)
            if not jpath or not jpath.exists():
                QMessageBox.critical(
                    None, "Clause Checker",
                    f"Data file was not found for {department} / {reinsurer}.\n"
                    f"Expected: {str(jpath) if jpath else '(no mapping)'}"
                )
                # Go back to reinsurer selection without logging out
                continue

            # ----- INPUT/COMPARE LOOP (Back from Input returns to Reinsurer) -----
            prev_text = ""
            while True:
                inp = InfoInputDialog(department, reinsurer, prev_text)
                if not inp.exec():
                    # Back pressed → return to reinsurer selection (same user session)
                    break

                text = inp.text()
                prev_text = text  # remember if user comes back from Comparison
                lines = [ln.strip("•–- ").strip() for ln in text.splitlines() if ln.strip()]
                clauses = []
                try:
                    with open(jpath, "r", encoding="utf-8") as f:
                        clauses = json.load(f)
                except Exception:
                    clauses = []

                matches = best_unique_matches(lines, clauses, department)
                # ----- REVIEW CYCLE: Comparison <-> Final Review -----
                # Persisted choices across the cycle:
                override_set: set[int] = set()
                # Pre-check 'keep' for LM7 lines so they are preserved as-is
                keep_set: set[int] = {i for i, ln in enumerate(lines) if is_lm7_line(ln)}

                # ----- REVIEW CYCLE: Comparison <-> Final Review -----
                # Persisted choices across the cycle:
                override_set: set[int] = set()
                keep_set: set[int] = set()

                back_to_input = False
                back_to_reinsurer = False
                state = "comparison"
                while True:
                    if state == "comparison":
                        cmp = ComparisonDialog(
                            department, reinsurer, lines, matches, text,
                            initial_override_set=override_set,
                            initial_keep_set=keep_set
                        )
                        cmp_result = cmp.exec()
                        # capture any user changes
                        override_set = set(getattr(cmp, "override_set", override_set))
                        keep_set = set(getattr(cmp, "keep_set", keep_set))

                        if cmp_result == 2:
                            # Back to Input
                            back_to_input = True
                            break
                        elif cmp_result == 3:
                            # Forward to Final Review
                            state = "review"
                            continue
                        else:
                            # Closed Comparison → treat as finish, go back to reinsurer
                            back_to_reinsurer = True
                            break

                    elif state == "review":
                        fin = FinalReviewDialog(
                            department, reinsurer, [], [], lines, matches,
                            override_set=override_set, keep_set=keep_set
                        )
                        fr_result = fin.exec()
                        # Nothing to update from FinalReview (no toggles there), but carry sets anyway
                        override_set = set(getattr(fin, "override_set", override_set))
                        keep_set = set(getattr(fin, "keep_set", keep_set))

                        if fr_result == 2:
                            # Back to Comparison
                            state = "comparison"
                            continue
                        else:
                            # Closed Final Review → back to reinsurer
                            back_to_reinsurer = True
                            break

                if back_to_input:
                    # Return to Input box (with same text)
                    prev_text = text
                    continue

                # Otherwise fall back to Reinsurer selection
                break

        # end session loop → back to login


