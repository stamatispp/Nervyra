"""Clipboard helpers (RTF conversion for Outlook)."""

from __future__ import annotations


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