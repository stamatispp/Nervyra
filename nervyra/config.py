"""Static configuration for departments, data paths, and UI colors."""

from pathlib import Path

# ---------- Config ----------

DEPARTMENTS = [
    "Property / Special Risks",
    "Liability",
    "Life / PA & Medical",
    "Financial Lines",
    "PI",
    "Administration",  # admins
]

# Per-department reinsurers (others may be unused until they get data files)
REINSURERS_BY_DEPT: dict[str, list[str]] = {
    "Property / Special Risks": ["Zurich", "QBE", "SwiftRE"],
    "Liability":                ["Kiln", "QBE", "SwiftRE"],
    "Life / PA & Medical":      ["Zurich", "QBE", "SwiftRE"],
    "Financial Lines":          ["Zurich", "QBE", "SwiftRE"],
    "PI":                       ["Zurich", "QBE", "SwiftRE"],
    "Administration":           [],  # Admin Console instead of reinsurers
}

USERS_FILE = "users.json"  # bundled fallback (next to EXE)

# External users.json (shared location on U: drive)
USERS_EXTERNAL_DIR = Path(r"U:\IT\APP\Nervyra")
USERS_EXTERNAL_PATH = USERS_EXTERNAL_DIR / "users.json"

# Clause files root for Property dept
CLAUSES_ROOT = Path(r"U:\IT\APP\Nervyra")
PROPERTY_DIR = CLAUSES_ROOT / "Property"
PROPERTY_FILENAMES = {
    "Zurich":  "Property_Zurich.json",
    "QBE":     "Property_QBE.json",
    "SwiftRE": "Property_SwiftRE.json",
}

# Clause files root for Liability dept
LIABILITY_DIR = CLAUSES_ROOT / "Liability"
LIABILITY_FILENAMES = {
    "Kiln":    "Liability_Kiln.json",
    "QBE":     "Liability_QBE.json",
    "SwiftRE": "Liability_SwiftRE.json",
}

# ---------- Custom colors ----------
CUSTOM_BLUE = "#6EADFF"
CUSTOM_BLUE_RGB = "rgb(110,173,255)"
META_GREY   = "#9aa0a6"

# ---------- Windows taskbar icon ----------