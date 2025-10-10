import sys, os, json, unicodedata, re, binascii, hashlib
from pathlib import Path
from html import escape

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
    QLabel, QTextEdit, QMessageBox, QWidget, QScrollArea, QToolButton, QLineEdit,
    QCheckBox
)
from PySide6.QtGui import QIcon, QFont, QClipboard, QGuiApplication
from PySide6.QtCore import Qt, QMimeData

# --- Qt resources (compile once: pyside6-rcc resources.qrc -o resources_rc.py)
# resources.qrc should include: <RCC><qresource prefix="/icons"><file>icon.ico</file></qresource></RCC>
import resources_rc  # provides :/icons/icon.ico

# ---------- Global runtime context (set after login) ----------
CURRENT_USER = {"username": None, "department": None, "is_admin": False}

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
def set_appusermodel_id(app_id: str = "Nervyra.ClauseChecker"):
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

# ---------- Paths ----------
def app_dir() -> str:
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0])))

def res_path(name: str) -> str:
    return os.path.join(app_dir(), name)

def users_path() -> str:
    return str(USERS_EXTERNAL_PATH)

def clause_json_path(department: str, reinsurer: str) -> Path | None:
    r"""
    Map (department, reinsurer) to the expected JSON path.
    Property files live under:  U:\IT\APP\Nervyra\Property\Property_<Reinsurer>.json
    Liability files live under: U:\IT\APP\Nervyra\Liability\Liability_<Reinsurer>.json
    """
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

    # Other departments: (no external files yet)
    return None

def app_icon() -> QIcon:
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

# ---------- Users / Login ----------
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
    salt = binascii.unhexlify(salt_hex.encode("ascii"))
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return binascii.hexlify(dk).decode("ascii")

def verify_login(users: dict, username: str, password: str) -> tuple[bool, str | None, bool]:
    """
    Returns (ok, department_if_ok, is_admin)
    users.json per user:
    {
      "username": {
        "department": "...",
        "salt": "hex",
        "hash": "hex"
      }
    }
    """
    rec = users.get(username.lower())
    if not rec:
        return (False, None, False)
    salt = rec.get("salt", "")
    good_hash = rec.get("hash", "")
    if not salt or not good_hash:
        return (False, None, False)
    calc = pbkdf2_hash(password, salt)
    if calc == good_hash:
        dept = rec.get("department")
        is_admin = (dept == "Administration")
        return (True, dept, is_admin)
    return (False, None, False)

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nervyra – Login")
        self.setMinimumWidth(360)
        ic = app_icon()
        if not ic.isNull():
            self.setWindowIcon(ic)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Username:"))
        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("e.g., osama")
        lay.addWidget(self.user_edit)

        lay.addWidget(QLabel("Password:"))
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)
        lay.addWidget(self.pass_edit)

        row = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.ok_btn = QPushButton("Login")

        # --- Make Login the default action when pressing Enter ---
        self.ok_btn.setDefault(True)
        self.ok_btn.setAutoDefault(True)
        self.cancel_btn.setAutoDefault(False)

        # Pressing Enter in either field triggers Login
        self.user_edit.returnPressed.connect(self.ok_btn.click)
        self.pass_edit.returnPressed.connect(self.ok_btn.click)

        # Wire up clicks
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self.accept)

        row.addStretch()
        row.addWidget(self.cancel_btn)
        row.addWidget(self.ok_btn)
        lay.addLayout(row)

        # Start focus in the username box
        self.user_edit.setFocus()

    def creds(self) -> tuple[str, str]:
        return self.user_edit.text().strip(), self.pass_edit.text()


# ---------- Admin: Create User dialog ----------
def make_user_record(username: str, password: str, department: str) -> tuple[str, dict]:
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 150_000)
    rec = {
        "department": department,
        "salt": binascii.hexlify(salt).decode("ascii"),
        "hash": binascii.hexlify(h).decode("ascii"),
    }
    return username.lower(), rec

class UserCreator(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Nervyra – Create User")
        self.setMinimumWidth(420)
        self.users = load_users()
        root = QVBoxLayout(self)

        root.addWidget(QLabel("Username (stored in lowercase):"))
        self.user_edit = QLineEdit(); self.user_edit.setPlaceholderText("e.g., lina")
        root.addWidget(self.user_edit)

        pw_row = QHBoxLayout()
        col1 = QVBoxLayout(); col2 = QVBoxLayout()
        col1.addWidget(QLabel("Password:"))
        self.pass_edit = QLineEdit(); self.pass_edit.setEchoMode(QLineEdit.Password)
        col1.addWidget(self.pass_edit)
        col2.addWidget(QLabel("Confirm password:"))
        self.pass2_edit = QLineEdit(); self.pass2_edit.setEchoMode(QLineEdit.Password)
        col2.addWidget(self.pass2_edit)
        pw_row.addLayout(col1); pw_row.addLayout(col2); root.addLayout(pw_row)

        show_cb = QCheckBox("Show password")
        show_cb.toggled.connect(
            lambda on: [w.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)
                        for w in (self.pass_edit, self.pass2_edit)]
        )
        root.addWidget(show_cb)

        root.addWidget(QLabel("Department:"))
        self.dept_combo = QComboBox()
        self.dept_combo.addItems(DEPARTMENTS)
        root.addWidget(self.dept_combo)

        # --- Buttons ---
        btn_row = QHBoxLayout()
        self.cancel_btn = QPushButton("Close")
        self.save_btn = QPushButton("Save User")

        # Make "Save User" the default action (Enter will trigger this)
        self.save_btn.setDefault(True)
        self.save_btn.setAutoDefault(True)
        self.cancel_btn.setAutoDefault(False)

        btn_row.addStretch()
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.save_btn)
        root.addLayout(btn_row)

        # Wire up clicks
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self.save_user)

        # Pressing Enter in any text field triggers "Save User"
        self.user_edit.returnPressed.connect(self.save_btn.click)
        self.pass_edit.returnPressed.connect(self.save_btn.click)
        self.pass2_edit.returnPressed.connect(self.save_btn.click)

        # Initial focus
        self.user_edit.setFocus()

    def error(self, msg: str): QMessageBox.critical(self, "Error", msg)
    def info(self, msg: str): QMessageBox.information(self, "Info", msg)
    def warn(self, msg: str) -> bool:
        return QMessageBox.question(
            self, "Confirm", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) == QMessageBox.Yes

    def save_user(self):
        username = self.user_edit.text().strip().lower()
        pw, pw2 = self.pass_edit.text(), self.pass2_edit.text()
        dept = self.dept_combo.currentText()

        if not username:
            return self.error("Please enter a username.")
        if " " in username:
            return self.error("Username cannot contain spaces.")
        if not pw:
            return self.error("Please enter a password.")
        if pw != pw2:
            return self.error("Passwords do not match.")
        if len(pw) < 6:
            return self.error("Password should be at least 6 characters.")
        if dept not in DEPARTMENTS:
            return self.error("Please choose a valid department.")

        exists = username in self.users
        if exists and not self.warn(f"User '{username}' exists. Overwrite?"):
            return

        key, record = make_user_record(username, pw, dept)
        self.users[key] = record
        try:
            save_users(self.users)
        except Exception as e:
            return self.error(f"Failed to save users.json:\n{e}")

        self.users = load_users()  # refresh from disk

        self.info(f"User '{key}' saved.\n{users_path()}")
        self.user_edit.clear()
        self.pass_edit.clear()
        self.pass2_edit.clear()
        self.user_edit.setFocus()


# ---------- Tiny admin header helper ----------
def maybe_admin_header(parent_dialog: QDialog) -> QWidget | None:
    """If current user is admin, return a header widget with 'Create User' button (right-aligned)."""
    if not CURRENT_USER.get("is_admin"):
        return None
    header = QWidget(parent_dialog)
    h = QHBoxLayout(header); h.setContentsMargins(0, 0, 0, 0)
    h.addWidget(QLabel(f"<b>User:</b> {CURRENT_USER.get('username','')} &nbsp; "
                       f"<b>Dept:</b> {CURRENT_USER.get('department','')}"))
    h.addStretch()
    btn = QPushButton("Create User")
    btn.setToolTip("Add a new Nervyra user (admins only)")
    btn.clicked.connect(lambda: UserCreator(parent_dialog).exec())
    h.addWidget(btn)
    return header

# ---------- Color normalizer ----------
def normalize_colors_keep_exact(html: str) -> str:
    def _fix_style(m):
        style = m.group(0)
        style = re.sub(r"color\s*:\s*#[0-9a-fA-F]{6}",
                       f"color: {CUSTOM_BLUE_RGB}", style, flags=re.IGNORECASE)
        style = re.sub(r"color\s*:\s*rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)",
                       f"color: {CUSTOM_BLUE_RGB}", style, flags=re.IGNORECASE)
        if "mso-themecolor" not in style:
            if not style.rstrip().endswith(";"):
                style += ";"
            style += " mso-themecolor:none; mso-themeshade:0;"
        return style
    html = re.sub(r'style\s*=\s*"[^"]*"', _fix_style, html, flags=re.IGNORECASE)
    html = re.sub(r"style\s*=\s*'[^']*'", _fix_style, html, flags=re.IGNORECASE)
    html = re.sub(r'(<font[^>]*\bcolor\s*=\s*")[^"]+(")',
                  rf'\1{CUSTOM_BLUE}\2', html, flags=re.IGNORECASE)
    return html
    
    # --- Protected wording detectors ---
LM7_PATTERN = re.compile(r"\blm[\s\-]*7\b", re.IGNORECASE)
PAYMENT_WARRANTY_PATTERN = re.compile(r"\bpayment\s*[-/]?\s*warranty\b", re.IGNORECASE)

def is_payment_warranty_line(text: str) -> bool:
    """Treat lines containing 'Payment Warranty' (incl. 'payment-warranty' or 'payment/warranty') as unmatchable."""
    return bool(PAYMENT_WARRANTY_PATTERN.search(text or ""))
    
def is_lm7_line(text: str) -> bool:
    return bool(LM7_PATTERN.search(text or ""))

    # Treat any line containing "Temporary" as unmatchable
TEMPORARY_PATTERN = re.compile(r"\btemporary\b", re.IGNORECASE)

def is_temporary_line(text: str) -> bool:
    return bool(TEMPORARY_PATTERN.search(text or ""))
    


# ===================== MATCHING HELPERS (HARDENED) =====================
def clean_text(text: str) -> str:
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = unicodedata.normalize("NFKD", text)
    return "".join(c if (c.isalnum() or c.isspace()) else " " for c in text.lower())

# Expanded stopwords to de-emphasize generic timing/notice terms and boilerplate
COMMON_STOPWORDS: set[str] = {
    "and","or","of","the","clause","limit","value","in","property","policy","insured","insurance","company",
    "be","is","are","to","for","on","by","with","at","an","a","as","it","this","that","shall","may","each",
    # timing/notice boilerplate
    "day","days","notice","within","period","time","any","event","request","portion","been","force",
    "subject","also","terms","agreement","applicable","provided","always","no","refund","allowed","upon",
    # frequent fillers
    "per","up","such","but","not","from","last","known","address","letter","registered","adjusted","pro","rata",
    "short","long","term","if","has","under","cost","costs","loss"
}

def normalize_user_text(text: str) -> str:
    return clean_text(text)

def _is_numeric_token(tok: str) -> bool:
    # pure numeric tokens (e.g., "30", "15", "100") are considered weak and removed
    return tok.isdigit()
    
def singularize(tok: str) -> str:
    """
    Very light plural → singular normalizer.
    No synonyms; purely morphological.
    """
    t = tok.lower()
    if len(t) <= 3:
        return t
    if t.endswith("ies") and len(t) > 4:      # policies -> policy
        return t[:-3] + "y"
    for suf in ("sses", "xes", "zes", "ches", "shes"):  # clauses -> clause, classes -> class
        if t.endswith(suf):
            return t[:-2]
    if t.endswith("es") and not t.endswith(("aes", "ees", "oes")) and len(t) > 4:
        return t[:-2]
    if t.endswith("s") and not t.endswith("ss"):        # errors -> error (but keep loss -> loss)
        return t[:-1]
    return t



def token_set(s: str, stopwords: set[str]) -> set[str]:
    # Drop stopwords, numbers, very short tokens; normalize to singular only.
    toks = []
    for w in clean_text(s).split():
        if not w:
            continue
        if w.isdigit():
            continue
        if len(w) <= 2:
            continue
        w = singularize(w)              # <-- singular/plural only
        if w in stopwords:
            continue
        toks.append(w)
    return set(toks)



def clause_token_pool(clause: dict, stopwords: set[str]) -> set[str]:
    name_tokens = token_set(clause.get("Name of Clause", ""), stopwords)
    kw_tokens = set()
    for kw in clause.get("Keywords", []):
        kw_tokens |= token_set(kw, stopwords)
    return name_tokens | kw_tokens

def match_clause_with_score(user_text: str, clauses: list[dict]) -> tuple[dict | None, int]:
    """
    Score = 10 * overlap_with(name+keywords) + 5 * overlap_with(name_only)
    Numbers and generic timing words are ignored upfront.
    """
    # Do not match/change LM7 wording lines at all
    if is_lm7_line(user_text):
        return (None, 0)

    # Lines mentioning "Temporary" should be left as NO MATCH
    if is_temporary_line(user_text):
        return (None, 0)
        
    # Lines mentioning "Payment Warranty" should be left as NO MATCH    
    if is_payment_warranty_line(user_text):   # NEW
        return (None, 0)
        
    stopwords = set(COMMON_STOPWORDS)
    user_words = token_set(user_text, stopwords)
    if not user_words:
        return (None, 0)

    best_match, best_score = None, 0
    for clause in clauses:
        name_tokens = token_set(clause.get("Name of Clause", ""), stopwords)
        pool = name_tokens | token_set(" ".join(clause.get("Keywords", [])), stopwords)

        base_overlap = len(user_words & pool)
        name_overlap = len(user_words & name_tokens)

        # Weighted score: names matter more than generic keywords
        score = 10 * base_overlap + 5 * name_overlap

        # Small tie-breaker: prefer shorter names (more specific) on equal score
        if score > best_score or (score == best_score and best_match and len(clause.get("Name of Clause","")) < len(best_match.get("Name of Clause",""))):
            best_score, best_match = score, clause

    # require at least 1 strong signal (after filtering). If zero → no match
    return (best_match, best_score) if best_score >= 10 else (None, 0)
# =================== END MATCHING HELPERS (HARDENED) ===================

def clause_display_text(clause: dict, department: str) -> str:
    """How to render a clause in the UI (Liability may have empty limits)."""
    name = clause.get("Name of Clause", "").strip()
    limit = (clause.get("Limit") or "").strip()

    # For Liability, ignore limit in matching, but still display it if it exists
    if department == "Liability":
        if limit:
            return f"{name} – {limit}"
        return name

    # For Property and others, always show name + limit (if any)
    if limit:
        return f"{name} – {limit}"
    return name

def best_unique_matches(user_lines: list[str], clauses: list[dict], department: str) -> list[dict | None]:
    """
    For Property: uniqueness key = (Name, Limit)
    For Liability: uniqueness key = (Name)  [ignore Limit entirely]
    """
    line_results: list[tuple[dict | None, int]] = [
        match_clause_with_score(ln, clauses) for ln in user_lines
    ]

    best_for_key: dict[tuple[str, ...], tuple[int, int]] = {}
    for idx, (m, score) in enumerate(line_results):
        if not m:
            continue
        if department == "Liability":
            key = (m.get("Name of Clause", ""),)  # by Name only
        else:
            key = (m.get("Name of Clause", ""), m.get("Limit", ""))  # Name+Limit
        if key not in best_for_key or score > best_for_key[key][1]:
            best_for_key[key] = (idx, score)

    final: list[dict | None] = []
    for idx, (m, _score) in enumerate(line_results):
        if not m:
            final.append(None)
            continue
        if department == "Liability":
            key = (m.get("Name of Clause", ""),)
        else:
            key = (m.get("Name of Clause", ""), m.get("Limit", ""))
        winner_idx, _ = best_for_key[key]
        final.append(m if idx == winner_idx else None)
    return final

def compute_matched_tokens(user_text: str, clause: dict) -> list[str]:
    stopwords = set(COMMON_STOPWORDS)
    user_words = token_set(user_text, stopwords)
    pool = clause_token_pool(clause, stopwords)
    return sorted(user_words & pool)

def highlight_autocompleted(user_text: str, matched_text: str) -> str:
    # Plural-aware highlight only (no synonyms)
    raw_user = normalize_user_text(user_text).split()
    user_words_norm = {singularize(t.strip(".,;:!?").lower()) for t in raw_user}

    out = []
    for word in matched_text.split():
        stripped = word.strip(".,;:!?").lower()
        if singularize(stripped) in user_words_norm:
            out.append(word)
        else:
            out.append(f"<span style='color:{CUSTOM_BLUE};'>{word}</span>")
    return " ".join(out)


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
def _rtf_escape(s: str) -> str:
    return s.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")

def _html_fragment_to_rtf(fragment: str) -> str:
    import re as _re
    txt = fragment
    txt = txt.replace("&nbsp;", " ")
    txt = _re.sub(r"(?i)<br\s*/?>", "\n", txt)

    out = []
    pos = 0
    stack = []

    for m in _re.finditer(r"(?is)<(/?)span\b([^>]*)>|<[^>]+>", txt):
        chunk = txt[pos:m.start()]
        if chunk:
            out.append(_rtf_escape(chunk))
        tag = m.group(0)
        attrs = m.group(2) or ""
        pos = m.end()

        if tag.lower().startswith("</span"):
            if stack:
                top = stack.pop()
                if top.get("strike"): out.append(r"\strike0 ")
                if top.get("blue"):   out.append(r"\cf0 ")
        elif tag.lower().startswith("<span"):
            style = attrs.replace("&quot;", '"')
            style_up = style.upper()
            style_lo = style.lower()
            blue = ("#6EADFF" in style_up) or ("110,173,255" in style_up)
            strike = ("line-through" in style_lo)
            flags = {}
            if blue:
                out.append(r"\cf1 "); flags["blue"] = True
            if strike:
                out.append(r"\strike "); flags["strike"] = True
            stack.append(flags)

    if pos < len(txt):
        out.append(_rtf_escape(txt[pos:]))

    while stack:
        top = stack.pop()
        if top.get("strike"): out.append(r"\strike0 ")
        if top.get("blue"):   out.append(r"\cf0 ")

    return "".join(out)

def build_rtf_bullets_from_items(items_sorted: list[dict]) -> bytes:
    parts = [
        r"{\rtf1\ansi\ansicpg1252\uc1\deff0",
        r"{\fonttbl{\f0 Calibri;}}",
        r"{\colortbl ;\red110\green173\blue255;}",
        r"\viewkind4\pard\plain\ltrpar\sa0\sl0\f0\fs22"
    ]
    for c in items_sorted:
        parts.append(r"\par ")
        parts.append(r"\bullet\tab ")
        parts.append(_html_fragment_to_rtf(c['html']))
        parts.append(r"\cf0\strike0 ")
    parts.append("}")
    return "".join(parts).encode("latin-1", errors="ignore")

# ---------- UI ----------
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

# ---------- Main ----------
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

if __name__ == "__main__":
    main()
