from __future__ import annotations

import json
import logging
import re
import urllib.request
import webbrowser
from typing import Dict, Any

from . import __version__

log = logging.getLogger(__name__)

# Change this if you fork / move the repo
GITHUB_REPO = "stamatispp/Nervyra"

def _parse_version(v: str):
    # Accept 'v1.2.0' or '1.2.0'
    v = v.strip()
    v = v[1:] if v.lower().startswith("v") else v
    parts = re.split(r"[.+-]", v)
    nums = []
    for p in parts[0].split("."):
        try:
            nums.append(int(p))
        except Exception:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])

def check_for_updates() -> Dict[str, Any]:
    """Lightweight update checker (framework). Returns info dict.

    Note: this does NOT self-update automatically; it just checks latest GitHub release.
    """
    api = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    req = urllib.request.Request(api, headers={"User-Agent": "Nervyra"})
    with urllib.request.urlopen(req, timeout=5) as r:
        data = json.loads(r.read().decode("utf-8", errors="replace"))

    latest_tag = str(data.get("tag_name", "")).strip() or str(data.get("name", "")).strip()
    latest = latest_tag or "0.0.0"

    current_v = _parse_version(__version__)
    latest_v = _parse_version(latest)

    notes = str(data.get("body", "") or "")
    html_url = str(data.get("html_url", "") or "")

    return {
        "current_version": __version__,
        "latest_version": latest,
        "update_available": latest_v > current_v,
        "release_notes": notes,
        "release_url": html_url,
    }

def open_releases_page() -> None:
    webbrowser.open(f"https://github.com/{GITHUB_REPO}/releases")
