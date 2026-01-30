"""Main application dialogs (selector, input, comparison, review, admin console)."""

from __future__ import annotations

import json
from html import escape
from html import escape

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
    QLabel, QTextEdit, QMessageBox, QWidget, QScrollArea, QToolButton, QLineEdit,
    QCheckBox
)
from PySide6.QtGui import QFont, QClipboard, QGuiApplication
from PySide6.QtCore import Qt, QMimeData

from ..paths import app_icon, clause_json_path
from ..config import CUSTOM_BLUE
from ..state import CURRENT_USER
from ..clause_engine import (
    best_unique_matches,
    compute_matched_tokens,
    highlight_autocompleted,
    clause_display_text,
    is_lm7_line,
    normalize_colors_keep_exact,
    is_payment_warranty_line,
    is_temporary_line,
)
from ..clipboard_utils import build_rtf_bullets_from_items
from .common import make_square_toggle, meta_line
from .admin_header import maybe_admin_header
from .user_creator import UserCreator


class BaseDialog(QDialog):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        ic = app_icon()
        if not ic.isNull():
            self.setWindowIcon(ic)
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)

class ReinsurerSelectorDialog(BaseDialog):
    def __init__(self, department_name: str, reinsurers_for_dept: list[str], *, allow_logout: bool = True):
        super().__init__()
        self.department_name = department_name
        self.setWindowTitle(f"Clause Checker – Select Reinsurer ({department_name})")
        self.setMinimumWidth(360)
        lay = QVBoxLayout(self)

        hdr = maybe_admin_header(self)
        if hdr:
            lay.addWidget(hdr)

        lay.addWidget(QLabel(f"Department: {department_name}"))
        lay.addWidget(QLabel("Choose a reinsurer:"))
        self.combo = QComboBox()
        self.combo.addItems(reinsurers_for_dept)
        lay.addWidget(self.combo)

        row = QHBoxLayout()
        self.back_or_logout_btn = QPushButton("Logout" if allow_logout else "Back")
        self.nxt_btn = QPushButton("Next")

        # Make "Next" the default (Enter will trigger this)
        self.nxt_btn.setDefault(True)
        self.nxt_btn.setAutoDefault(True)
        self.back_or_logout_btn.setAutoDefault(False)

        if allow_logout:
            self.back_or_logout_btn.setToolTip("Logout and switch user")
            self.back_or_logout_btn.clicked.connect(self.reject)  # QDialog.Rejected → true logout
        else:
            self.back_or_logout_btn.setToolTip("Back to previous step")
            self.back_or_logout_btn.clicked.connect(lambda: self.done(2))  # custom result=2 for Back

        self.nxt_btn.clicked.connect(self.accept)

        row.addWidget(self.back_or_logout_btn)
        row.addStretch()
        row.addWidget(self.nxt_btn)
        lay.addLayout(row)

        # Hitting Enter in the combo box will also trigger Next
        self.combo.activated.connect(lambda: self.nxt_btn.click())

    def selected(self):
        return self.combo.currentText()


class InfoInputDialog(BaseDialog):
    def __init__(self, department_name: str, reinsurer_name: str, prev_text: str = ""):
        super().__init__()
        self.department_name, self.reinsurer_name = department_name, reinsurer_name
        self.setWindowTitle(f"Input Clause – {department_name} / {reinsurer_name}")
        self.setMinimumSize(600, 400)
        lay = QVBoxLayout(self)

        hdr = maybe_admin_header(self)
        if hdr:
            lay.addWidget(hdr)

        lay.addWidget(QLabel(f"Enter clause info for {department_name} / {reinsurer_name}:"))
        self.edit = QTextEdit()
        self.edit.setPlaceholderText("Type or paste clause text here...")
        self.edit.setAcceptRichText(False)
        self.edit.setPlainText(prev_text)
        lay.addWidget(self.edit, 1)

        row = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.next_btn = QPushButton("Analyze")

        # Default = Analyze
        self.next_btn.setDefault(True)
        self.next_btn.setAutoDefault(True)
        self.back_btn.setAutoDefault(False)

        self.back_btn.clicked.connect(self.reject)   # Back to reinsurer selection
        self.next_btn.clicked.connect(self.accept)
        row.addWidget(self.back_btn)
        row.addStretch()
        row.addWidget(self.next_btn)
        lay.addLayout(row)

    def text(self):
        return self.edit.toPlainText()


class ComparisonDialog(BaseDialog):
    """
    Shows user_lines vs autocompleted matches and lets user:
      - For matched lines: override autocomplete (keep original) via red X toggle.
      - For unmatched lines: keep the original line via blue toggle.

    New behavior for matched rows:
      - Clicking the text (label) selects the AUTOCOMPLETE (no strike).
      - Clicking the red X keeps USER INPUT (autocomplete text is struck-through).

    Persists state via override_set / keep_set (indices).
    """
    def __init__(self, department_name: str, reinsurer_name: str, user_lines, matches, original_text: str,
                 initial_override_set: set[int] | None = None,
                 initial_keep_set: set[int] | None = None):
        super().__init__()
        self.department_name, self.reinsurer_name = department_name, reinsurer_name
        we = f"({department_name} / {reinsurer_name})"
        self.setWindowTitle(f"Clause Match – Comparison {we}")
        self.setMinimumSize(900, 560)
        self.user_lines, self.matches = user_lines, matches
        self.original_text = original_text

        self.keep_buttons: list[tuple[QToolButton, int]] = []       # (btn, idx)
        self.override_buttons: list[tuple[QToolButton, int]] = []   # (btn, idx)

        # Track per-row widgets/data for matched rows so we can refresh label HTML
        self._matched_rows: dict[int, dict] = {}  # idx -> {"label": QLabel, "tokens": list[str], "uline": str, "match": dict, "btn": QToolButton}

        # sets we carry in/out
        self.override_set: set[int] = set(initial_override_set or set())
        self.keep_set: set[int] = set(initial_keep_set or set())

        main = QVBoxLayout(self)
        hdr = maybe_admin_header(self)
        if hdr:
            main.addWidget(hdr)

        cols = QHBoxLayout()
        main.addLayout(cols)

        # Left column: read-only raw user input (not interactive per line)
        left_col = QVBoxLayout()
        left_col.addWidget(QLabel("User Input"))
        self.left_box = QTextEdit(); self.left_box.setReadOnly(True)
        self.left_box.setPlainText("\n".join(user_lines))
        left_col.addWidget(self.left_box); cols.addLayout(left_col, 1)

        # Right column: per-line comparison controls
        right_col = QVBoxLayout()
        right_col.addWidget(QLabel(f"Autocompleted ({self.reinsurer_name})"))
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        container = QWidget(); v = QVBoxLayout(container); v.setSpacing(12)

        for idx, (uline, match) in enumerate(zip(user_lines, matches)):
            row = QWidget(); h = QHBoxLayout(row); h.setContentsMargins(0,0,0,0)

            if match:
                # Rich label that we will update (strike/no-strike) depending on toggle
                lbl = QLabel(); lbl.setWordWrap(True); lbl.setTextFormat(Qt.RichText)

                tokens = compute_matched_tokens(uline, match)
                # Create the red-X toggle (override = keep user input)
                override_btn = make_square_toggle(
                    tooltip="Click to KEEP your original text instead of the autocomplete.",
                    red_when_checked=True
                )
                # initial state
                override_btn.setChecked(idx in self.override_set)

                # Save row parts so we can refresh on toggle / clicks
                self._matched_rows[idx] = {
                    "label": lbl,
                    "tokens": tokens,
                    "uline": uline,
                    "match": match,
                    "btn": override_btn
                }

                # Helper to compute and set the label's HTML based on current override state
                def _update_label_for_idx(i=idx):
                    data = self._matched_rows[i]
                    use_override = data["btn"].isChecked()
                    uline_i = data["uline"]
                    match_i = data["match"]
                    # Base autocomplete text (with blue highlighting of matched parts)
                    display_txt = clause_display_text(match_i, self.department_name)
                    base_html = highlight_autocompleted(uline_i, display_txt)
                    # If overriding (keeping user input), visually strike the autocomplete text
                    if use_override:
                        meta = meta_line(data["tokens"])
                        base_no_meta = base_html.replace(meta, "")
                        html = (
                            f"<span style='text-decoration:line-through; opacity:0.6;'>{base_no_meta}</span>"
                            f"<span style='margin-left:8px; color:#c0392b;'>(kept original)</span>"
                            f"{meta}"
                        )
                    else:
                        html = base_html
                    data["label"].setText(html)

                # Connect the toggle to update the label
                override_btn.toggled.connect(_update_label_for_idx)

                # Make clicking on the label choose AUTOCOMPLETE (i.e., uncheck the red X)
                def _label_mouse_press(event, i=idx):
                    data = self._matched_rows[i]
                    if data["btn"].isChecked():
                        data["btn"].setChecked(False)  # choosing autocomplete
                    else:
                        _update_label_for_idx()
                    QLabel.mousePressEvent(data["label"], event)

                lbl.mousePressEvent = _label_mouse_press

                # Initial render
                _update_label_for_idx()

                # Lay out: label on left, red X on right
                h.addWidget(lbl, 1)
                self.override_buttons.append((override_btn, idx))
                h.addWidget(override_btn, 0, Qt.AlignRight | Qt.AlignTop)

            else:
                # Unmatched: keep toggle (blue) + explanatory label
                keep_btn = make_square_toggle(
                    tooltip="Click to KEEP this line even though no match was found.", red_when_checked=False
    )
                # If it's an LM7 line, it should already be in self.keep_set from main(); this keeps it checked.
                keep_btn.setChecked(idx in self.keep_set)
                self.keep_buttons.append((keep_btn, idx))
                h.addWidget(keep_btn, 0, Qt.AlignLeft | Qt.AlignTop)

                if is_lm7_line(uline):
                    # Make it explicit that LM7 is left untouched
                    lbl = QLabel(f"<b>LM7 wording detected</b> — left unchanged:<br>{escape(uline)}")
                else:
                    lbl = QLabel(f"<span style='color:{CUSTOM_BLUE};'>No match found for:</span> {uline}")
                lbl.setWordWrap(True); lbl.setTextFormat(Qt.RichText)
                h.addWidget(lbl, 1)


            v.addWidget(row)

        v.addStretch(); scroll.setWidget(container)
        right_col.addWidget(scroll); cols.addLayout(right_col, 1)

        # Footer actions
        row = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.nxt_btn = QPushButton("Next")

        # Default = Next
        self.nxt_btn.setDefault(True)
        self.nxt_btn.setAutoDefault(True)
        self.back_btn.setAutoDefault(False)

        self.back_btn.clicked.connect(self.go_back)
        self.nxt_btn.clicked.connect(self.go_next)

        row.addWidget(self.back_btn)
        row.addStretch()
        row.addWidget(self.nxt_btn)
        main.addLayout(row)

    def _capture_choices(self):
        # rebuild sets from current button states
        self.override_set = {idx for (btn, idx) in self.override_buttons if btn.isChecked()}
        self.keep_set = {idx for (btn, idx) in self.keep_buttons if btn.isChecked()}

    def go_next(self):
        self._capture_choices()
        self.done(3)  # FORWARD_TO_REVIEW

    def go_back(self):
        self._capture_choices()
        self.done(2)  # BACK_TO_INPUT


class FinalReviewDialog(BaseDialog):
    """
    Renders the final list according to decisions:
      - override_set: for matched lines, keep original text instead of autocomplete.
      - keep_set: for unmatched lines, keep the original (not struck out).
    """
    def __init__(self, department_name: str, reinsurer_name: str,
                 matched_items, rejected_items, user_lines, full_matches,
                 override_set: set[int] | None = None,
                 keep_set: set[int] | None = None):
        super().__init__()
        self.setWindowTitle(f"Final Clause Review ({department_name} / {reinsurer_name})")
        self.setMinimumSize(900, 560)
        self.department_name, self.reinsurer_name = department_name, reinsurer_name
        self.user_lines, self.full_matches = user_lines, full_matches

        # carry-through sets (no editing here, just keep them)
        self.override_set: set[int] = set(override_set or set())
        self.keep_set: set[int] = set(keep_set or set())

        main = QVBoxLayout(self)
        hdr = maybe_admin_header(self)
        if hdr: main.addWidget(hdr)

        cols = QHBoxLayout(); main.addLayout(cols)

        left_col = QVBoxLayout(); left_col.addWidget(QLabel("Matched Clauses (Name + Limit)"))
        self.left_box = QTextEdit(); self.left_box.setReadOnly(True)

        # Build items from full_matches + flags
        all_items = []
        for idx, match in enumerate(full_matches):
            uline = user_lines[idx]
            if match:
                if idx in self.override_set:
                    # user decided to keep their original text
                    html = uline  # plain
                    all_items.append({
                        "name": match["Name of Clause"],  # still sort by clause name for stability
                        "html": html,
                        "desc": match.get("Description", ""),
                        "kept": False,
                        "overridden": True,
                        "rejected": False
                    })
                else:
                    display_txt = clause_display_text(match, self.department_name)
                    html = highlight_autocompleted(uline, display_txt)
                    all_items.append({
                        "name": match["Name of Clause"],
                        "html": html,
                        "desc": match.get("Description", ""),
                        "kept": False,
                        "overridden": False,
                        "rejected": False
                    })
            else:
                if idx in self.keep_set:
                    # unmatched but kept
                    all_items.append({
                        "name": uline,
                        "html": uline,
                        "desc": "",
                        "kept": True,
                        "overridden": False,
                        "rejected": False
                    })
                else:
                    # unmatched and rejected (strike-through)
                    all_items.append({
                        "name": uline,
                        "html": f"<span style='color:{CUSTOM_BLUE}; text-decoration: line-through;'>{uline}</span>",
                        "desc": "",
                        "kept": False,
                        "overridden": False,
                        "rejected": True
                    })

        all_items_sorted = all_items
        self.all_items_sorted = all_items_sorted

        items_html = "".join(f"<li>{c['html']}</li>" for c in all_items_sorted)
        bulleted = (
            "<div style='font-family: Calibri; font-size: 11pt;'>"
            "<ul style='margin-top:0.25em; margin-left:1.2em; padding-left:0.8em; line-height:1.35;'>"
            f"{items_html}"
            "</ul>"
            "</div>"
        )
        self.left_box.document().setDefaultFont(QFont("Calibri", 11))
        self.left_box.setHtml(bulleted)
        left_col.addWidget(self.left_box); cols.addLayout(left_col,1)

        right_col = QVBoxLayout(); right_col.addWidget(QLabel("Descriptions"))
        self.right_box = QTextEdit(); self.right_box.setReadOnly(True)
        descs = []
        for c in all_items_sorted:
            if c["desc"] and not c["rejected"]:
                name_html = f"<b>{escape(c['name'])}</b>"
                # Preserve newlines from JSON descriptions
                desc_html_piece = escape(c["desc"]).replace("\n", "<br>")
                descs.append(f"{name_html}<br>{desc_html_piece}")
                
        desc_html = (
            "<div style='font-family: Calibri; font-size: 11pt; line-height:1.35;'>"
            + "<br><br>".join(descs) +
            "</div>"
        )
        self.right_box.document().setDefaultFont(QFont("Calibri", 11))
        self.right_box.setHtml(desc_html)
        right_col.addWidget(self.right_box); cols.addLayout(right_col,1)

        row = QHBoxLayout()
        back = QPushButton("Back to Comparison"); back.clicked.connect(self.go_back)
        copy_html = QPushButton("Copy (keep styling)")
        copy_html.setToolTip("Publishes RTF + HTML to preserve exact blue and strike-through in Word.")
        copy_html.clicked.connect(self.copy_bullets_html)
        close = QPushButton("Close"); close.clicked.connect(self.accept)
        row.addWidget(back); row.addStretch(); row.addWidget(copy_html); row.addWidget(close); main.addLayout(row)

    def copy_bullets_html(self):
        rtf_bytes = build_rtf_bullets_from_items(self.all_items_sorted)
        html = self.left_box.toHtml()
        html = normalize_colors_keep_exact(html)
        mime = QMimeData()
        mime.setData("text/rtf", rtf_bytes)
        mime.setData("application/rtf", rtf_bytes)
        mime.setHtml(html)
        mime.setText(self.left_box.toPlainText())
        QGuiApplication.clipboard().setMimeData(mime, QClipboard.Clipboard)

    def go_back(self):
        # Go back to Comparison (previous box), keeping current sets
        self.done(2)  # BACK_TO_COMPARISON

# ---------- Admin Console (for Administration dept) ----------
class AdminConsole(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nervyra – Administration")
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)

        hdr = maybe_admin_header(self)
        if hdr: lay.addWidget(hdr)

        lay.addWidget(QLabel("<b>Administration</b><br>"
                             "Create and manage Nervyra users."))
        row = QHBoxLayout()
        btn_close = QPushButton("Logout")
        btn_create = QPushButton("Create User")
        row.addStretch(); row.addWidget(btn_close); row.addWidget(btn_create)
        lay.addStretch(); lay.addLayout(row)

        btn_close.clicked.connect(self.accept)
        btn_create.clicked.connect(lambda: UserCreator(self).exec())
