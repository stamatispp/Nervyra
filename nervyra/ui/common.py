"""Small shared UI helpers."""

from __future__ import annotations

from PySide6.QtWidgets import QToolButton

from ..config import META_GREY, CUSTOM_BLUE


def meta_line(tokens: list[str]) -> str:
    if not tokens:
        return ""
    joined = ", ".join(tokens)
    return f"<div style='color:{META_GREY}; font-size:11px; margin-top:2px;'>Matched on: {joined}</div>"

# ---------- Tiny UI helper ----------
def make_square_toggle(size=18, tooltip="", red_when_checked=False) -> QToolButton:
    btn = QToolButton()
    btn.setCheckable(True)
    btn.setFixedSize(size, size)
    btn.setToolTip(tooltip)
    base = f"""
        QToolButton {{
            border: 1px solid #666;
            border-radius: 3px;
            background: #fff;
            font-weight: bold;
        }}
        QToolButton:hover {{ background: #f2f2f2; }}
        QToolButton:pressed {{ background: #e8e8e8; }}
    """
    if red_when_checked:
        extra = """
            QToolButton:checked {
                background: #ffebee;
                color: #c62828;
                border-color: #c62828;
            }
        """
        btn.setText("")
        btn.toggled.connect(lambda on: btn.setText("X" if on else ""))
        btn.setStyleSheet(base + extra)
    else:
        extra = f"""
            QToolButton:checked {{
                background: {CUSTOM_BLUE};
                color: white;
                border-color: #2b6fb3;
            }}
        """
        btn.setStyleSheet(base + extra)
    return btn

# ---------- RTF builders ----------
