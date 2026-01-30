"""Clause text normalization and matching engine."""

from __future__ import annotations

import json
import re
import unicodedata
from html import escape

from .config import CUSTOM_BLUE, CUSTOM_BLUE_RGB

# ---- HTML color normalization (keeps exact original intent) ----

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

