"""
Normalizes printed / handwritten question numbers so that variants like
"Q11(a)", "11 (a)", "11-A", "11a", "26(ii)", "26-ii" all resolve to the same
canonical key.

Canonical form: "<number>" or "<number>(<letters>)", lowercase.
Examples -> "11", "11(a)", "26(ii)"
"""
import re

_CLEAN_RE = re.compile(r"[\s._]+")
_Q_PREFIX_RE = re.compile(r"^q\.?\s*", re.IGNORECASE)
_PAREN_RE = re.compile(r"^(\d+)\s*[\(\-]?\s*([a-zA-Z]*)\)?$")


def normalize_question_number(raw: str) -> str:
    """Normalize a question number string to a canonical comparable form."""
    if not raw:
        return ""

    value = raw.strip()
    value = _Q_PREFIX_RE.sub("", value)
    value = _CLEAN_RE.sub("", value)
    value = value.replace(")", "").replace("(", "(")

    match = _PAREN_RE.match(value)
    if match:
        number, letter = match.groups()
        if letter:
            return f"{number}({letter.lower()})"
        return number

    # Fallback: strip all non-alphanumeric characters and lowercase.
    fallback = re.sub(r"[^a-zA-Z0-9]", "", value).lower()
    return fallback


def extract_order_key(normalized: str) -> tuple:
    """Produce a sortable key (main_number, sub_letter) from a normalized number."""
    match = re.match(r"^(\d+)(?:\(([a-z])\))?$", normalized)
    if not match:
        return (float("inf"), normalized)
    number, letter = match.groups()
    return (int(number), letter or "")
