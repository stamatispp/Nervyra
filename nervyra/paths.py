"""Path helpers and application icon utilities."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtGui import QIcon

from .config import (
    USERS_FILE,
    USERS_EXTERNAL_PATH,
    PROPERTY_DIR,
    PROPERTY_FILENAMES,
    LIABILITY_DIR,
    LIABILITY_FILENAMES,
)

def set_appusermodel_id(app_id: str = "Nervyra.ClauseChecker") -> None:
    """Set Windows taskbar AppUserModelID (safe no-op on non-Windows)."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass
    try:
        from PySide6.QtWinExtras import QtWin
        QtWin.setCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

def app_dir() -> str:
    """Return folder containing bundled resources (PyInstaller-aware)."""
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0])))

def res_path(name: str) -> str:
    return os.path.join(app_dir(), name)

def users_path() -> str:
    return str(USERS_EXTERNAL_PATH)

def clause_json_path(department: str, reinsurer: str) -> Path | None:
    """Map (department, reinsurer) to expected JSON path."""
    if department == "Property / Special Risks":
        fname = PROPERTY_FILENAMES.get(reinsurer)
        if not fname:
            return None
        return PROPERTY_DIR / fname

    if department == "Liability":
        fname = LIABILITY_FILENAMES.get(reinsurer)
        if not fname:
            return None
        return LIABILITY_DIR / fname

    return None

def app_icon() -> QIcon:
    """Load app icon from Qt resources first, then fall back to bundled files."""
    ic = QIcon(":/icons/icon.ico")
    if not ic.isNull():
        return ic
    for name in ("icon.ico", "icon.png"):
        p = res_path(name)
        if os.path.exists(p):
            ic = QIcon(p)
            if not ic.isNull():
                return ic
    return QIcon()
