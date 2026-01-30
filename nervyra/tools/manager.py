from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base import Tool

log = logging.getLogger(__name__)

DEFAULT_PLUGIN_DIRS = [
    Path(__file__).resolve().parents[2] / "plugins",  # project-root/plugins (next to main.py)
]

def _load_manifest(path: Path) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return data
    except Exception as e:
        log.exception("Failed reading manifest %s: %s", str(path), e)
        return None

def _resolve_entrypoint(ep: str):
    """ep like 'package.module:function'"""
    if ":" not in ep:
        raise ValueError(f"Invalid entrypoint '{ep}'. Expected 'module:function'.")
    mod, fn = ep.split(":", 1)
    m = importlib.import_module(mod)
    f = getattr(m, fn)
    return f

def discover_tools(extra_dirs: Optional[List[Path]] = None) -> List[Tool]:
    dirs = list(DEFAULT_PLUGIN_DIRS)
    if extra_dirs:
        dirs.extend(extra_dirs)

    tools: List[Tool] = []
    seen: set[str] = set()

    for d in dirs:
        if not d.exists():
            continue
        for manifest in d.rglob("manifest.json"):
            data = _load_manifest(manifest)
            if not data:
                continue

            try:
                tid = str(data.get("id", "")).strip()
                if not tid or tid in seen:
                    continue
                seen.add(tid)

                ep = str(data.get("entrypoint", "")).strip()
                entry = _resolve_entrypoint(ep) if ep else None

                tools.append(
                    Tool(
                        id=tid,
                        name=str(data.get("name", tid)),
                        description=str(data.get("description", "")),
                        icon=str(data.get("icon", "")),
                        entrypoint=entry,
                        category=str(data.get("category", "General")),
                        allowed_departments=data.get("allowed_departments"),
                        admin_only=bool(data.get("admin_only", False)),
                    )
                )
            except Exception as e:
                log.exception("Invalid plugin manifest %s: %s", str(manifest), e)

    # Sort by category then name for a clean dashboard
    tools.sort(key=lambda t: (t.category.lower(), t.name.lower()))
    return tools
