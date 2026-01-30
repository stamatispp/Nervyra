"""User storage + authentication (compatible with original main.py)."""

from __future__ import annotations

import binascii
import hashlib
import json
import os
from pathlib import Path

from .config import USERS_FILE, USERS_EXTERNAL_DIR, USERS_EXTERNAL_PATH
from .paths import res_path

def load_users() -> dict:
    """Load users: prefer external file, else fallback bundled, else {}."""
    if USERS_EXTERNAL_PATH.exists():
        try:
            with open(USERS_EXTERNAL_PATH, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
            pass

    bundled = Path(res_path(USERS_FILE))
    if bundled.exists():
        try:
            with open(bundled, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
            return {}

    return {}

def save_users(users: dict) -> None:
    """Always save to the external file; create folder if needed."""
    USERS_EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    with open(USERS_EXTERNAL_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def pbkdf2_hash(password: str, salt_hex: str, iterations: int = 150_000) -> str:
    """Return derived key hex using PBKDF2-HMAC-SHA256."""
    salt = binascii.unhexlify(salt_hex.encode("ascii"))
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return binascii.hexlify(dk).decode("ascii")

def verify_login(users: dict, username: str, password: str):
    rec = (users or {}).get(username)
    if not rec:
        return False, None, False
    salt_hex = rec.get("salt", "")
    hash_hex = rec.get("hash", "")
    dept = rec.get("department")
    is_admin = bool(rec.get("is_admin", False))
    try:
        test_hash = pbkdf2_hash(password, salt_hex)
    except Exception:
        return False, None, False
    return test_hash == hash_hex, dept, is_admin

def make_user_record(username: str, password: str, department: str, is_admin: bool = False) -> dict:
    salt_hex = binascii.hexlify(os.urandom(16)).decode("ascii")
    return {
        "salt": salt_hex,
        "hash": pbkdf2_hash(password, salt_hex),
        "department": department,
        "is_admin": bool(is_admin),
    }
