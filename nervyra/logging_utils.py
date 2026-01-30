from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QMessageBox

def app_data_dir(app_name: str = "Nervyra") -> Path:
    base = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
    # On Windows this becomes %APPDATA%\<Org>\<App> usually; ensure stable
    d = base / app_name
    d.mkdir(parents=True, exist_ok=True)
    return d

def configure_logging(app_name: str = "Nervyra", level: int = logging.INFO) -> Path:
    log_dir = app_data_dir(app_name) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "nervyra.log"

    # Avoid duplicate handlers in dev reloads
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(level)
    sh.setFormatter(fmt)

    root.addHandler(fh)
    root.addHandler(sh)

    logging.getLogger(__name__).info("Logging initialized at %s", str(log_file))
    return log_file

def _friendly_crash_message(exc: BaseException) -> str:
    return (
        "Something went wrong and Nervyra needs to close this action.\n\n"
        "A crash report was written to your logs folder.\n\n"
        f"Error: {type(exc).__name__}: {exc}"
    )

def install_crash_handler(app_name: str = "Nervyra") -> None:
    """Install a global exception hook that logs tracebacks and shows a friendly dialog."""
    log = logging.getLogger(__name__)

    def excepthook(exc_type, exc, tb):
        try:
            trace = "".join(traceback.format_exception(exc_type, exc, tb))
            log.exception("UNHANDLED EXCEPTION\n%s", trace)
        except Exception:
            pass

        try:
            QMessageBox.critical(None, "Nervyra - Unexpected error", _friendly_crash_message(exc))
        except Exception:
            # If Qt is not available yet, fallback to stderr
            sys.stderr.write(_friendly_crash_message(exc) + "\n")

    sys.excepthook = excepthook

def log_exception(context: str, exc: BaseException) -> None:
    logging.getLogger(__name__).exception("%s: %s", context, exc)
