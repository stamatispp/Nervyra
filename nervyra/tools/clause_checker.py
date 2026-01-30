from __future__ import annotations

import json
import logging
from PySide6.QtWidgets import QMessageBox, QDialog

from ..config import DEPARTMENTS, REINSURERS_BY_DEPT
from ..paths import clause_json_path
from ..state import CURRENT_USER
from ..ui.dialogs import (
    ReinsurerSelectorDialog,
    InfoInputDialog,
    ComparisonDialog,
    FinalReviewDialog,
    AdminConsole,
)
from ..clause_engine import best_unique_matches, is_lm7_line

log = logging.getLogger(__name__)

def run(context: dict) -> None:
    """Run the Clause Checker tool inside the logged-in session."""
    department = context.get("department")
    if department not in DEPARTMENTS:
        QMessageBox.critical(None, "Clause Checker", "Your department is not configured.")
        return

    reinsurers = REINSURERS_BY_DEPT.get(department, [])

    # Admin-like departments (no reinsurer mapping) open console
    if not reinsurers:
        AdminConsole().exec()
        return

    # ======= TOOL LOOP (until user backs out) =======
    while True:
        sel = ReinsurerSelectorDialog(department, reinsurers, allow_logout=False)
        sel_result = sel.exec()
        if sel_result != QDialog.Accepted:
            return  # back to dashboard

        reinsurer = sel.selected()
        jpath = clause_json_path(department, reinsurer)
        if not jpath or not jpath.exists():
            QMessageBox.critical(
                None,
                "Clause Checker",
                f"Data file was not found for {department} / {reinsurer}.\n"
                f"Expected: {str(jpath) if jpath else '(no mapping)'}",
            )
            continue

        prev_text = ""
        while True:
            inp = InfoInputDialog(department, reinsurer, prev_text)
            if not inp.exec():
                break  # back to reinsurer selection

            text = inp.text()
            prev_text = text

            lines = [ln.strip("•–- ").strip() for ln in text.splitlines() if ln.strip()]

            try:
                clauses = json.loads(jpath.read_text(encoding="utf-8"))
            except Exception as e:
                log.exception("Failed reading clauses JSON: %s", e)
                clauses = []

            matches = best_unique_matches(lines, clauses, department)

            override_set: set[int] = set()
            keep_set: set[int] = {i for i, ln in enumerate(lines) if is_lm7_line(ln)}

            state = "comparison"
            while True:
                if state == "comparison":
                    cmp = ComparisonDialog(
                        department,
                        reinsurer,
                        lines,
                        matches,
                        text,
                        initial_override_set=override_set,
                        initial_keep_set=keep_set,
                    )
                    cmp_result = cmp.exec()

                    override_set = set(getattr(cmp, "override_set", override_set))
                    keep_set = set(getattr(cmp, "keep_set", keep_set))

                    if cmp_result == 2:
                        # Back to Input
                        break
                    elif cmp_result == 3:
                        state = "review"
                        continue
                    else:
                        # Close -> back to reinsurer selection
                        state = "done"
                        break

                elif state == "review":
                    fin = FinalReviewDialog(
                        department,
                        reinsurer,
                        [],
                        [],
                        lines,
                        matches,
                        override_set=override_set,
                        keep_set=keep_set,
                    )
                    fr_result = fin.exec()
                    if fr_result == 2:
                        state = "comparison"
                        continue
                    else:
                        state = "done"
                        break

            if state == "done":
                break  # back to reinsurer selection
            else:
                # back to input
                prev_text = text
                continue
