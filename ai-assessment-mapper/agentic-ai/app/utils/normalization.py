"""
Normalizes printed / handwritten question numbers so that variants like
"Q11(a)", "11 (a)", "11-A", "11a", "26(ii)", "26-ii", "11(a)(i)" all resolve
to the same canonical key.

Canonical form: "<number>" or "<number>(<letters>)(<letters>)...", lowercase.
Examples -> "11", "11(a)", "26(ii)", "11(a)(i)"
"""
import re

_CLEAN_RE = re.compile(r"[\s._]+")
_Q_PREFIX_RE = re.compile(r"^q\.?\s*", re.IGNORECASE)
_HYPHEN_GROUP_RE = re.compile(r"^(\d+)\s*-\s*([a-zA-Z0-9]+)$")
_NUMBER_PREFIX_RE = re.compile(r"^(\d+)(.*)$")
# Sub-part groups allow digits too (not just letters): handwriting/OCR
# regularly confuses a letter sub-part with a similar-looking digit (a/4,
# o/0, l/1, s/5). Silently dropping such a group instead of preserving it
# for comparison means a garbled "7(4)" (really "7(a)") loses all signal
# and normalizes down to bare "7", which can never fuzzy-match "7(a)" -
# keeping it as "7(4)" at least gives the fuzzy-matching tier a real chance.
_LETTER_GROUP_RE = re.compile(r"\(?([a-zA-Z0-9]+)\)?")

# Real sub-part labels are single letters/digits ("a", "4") or short roman
# numerals ("i".."xiii", max 4 characters). Anything longer is stray text -
# e.g. a model that writes "5 continued" instead of repeating "5" for a
# continuation page - and must NOT be treated as a sub-part, or two
# continuation pages of the same answer will normalize to different keys
# and silently fail to be recognized as the same question.
_MAX_SUBPART_LABEL_LENGTH = 4


def normalize_question_number(raw: str) -> str:
    """Normalize a question number string to a canonical comparable form."""
    if not raw:
        return ""

    value = raw.strip()
    value = _Q_PREFIX_RE.sub("", value)
    value = _CLEAN_RE.sub("", value)

    # A single hyphen-separated sub-part ("11-a", "26-ii") becomes parenthesized
    # up front so the general parser below only has one shape to handle.
    hyphen_match = _HYPHEN_GROUP_RE.match(value)
    if hyphen_match:
        number, letters = hyphen_match.groups()
        value = f"{number}({letters.lower()})"

    match = _NUMBER_PREFIX_RE.match(value)
    if not match:
        # Doesn't even start with a number - fall back to a plain slug.
        return re.sub(r"[^a-zA-Z0-9]", "", value).lower()

    number, rest = match.groups()
    groups = [g for g in _LETTER_GROUP_RE.findall(rest) if len(g) <= _MAX_SUBPART_LABEL_LENGTH]
    if not groups:
        return number
    return number + "".join(f"({g.lower()})" for g in groups)


_ORDER_KEY_RE = re.compile(r"^(\d+)((?:\([a-z0-9]+\))*)$")
_ORDER_GROUP_RE = re.compile(r"\(([a-z0-9]+)\)")


def extract_order_key(normalized: str) -> tuple:
    """
    Produce a deterministic sortable key from a normalized number, so
    questions are always displayed in logical order regardless of what order
    the model happened to return them in.

    "10" < "10(a)" < "10(a)(i)" < "10(b)" < "11" - a bare parent sorts before
    its own sub-parts (shorter tuples sort first when they're a prefix of a
    longer one), sub-parts sort alphabetically by letter, and multi-letter
    roman-numeral-style labels ("i" < "ii" < "iii") sort correctly for the
    small ranges real exam papers use, since they compare by length first.
    """
    match = _ORDER_KEY_RE.match(normalized)
    if not match:
        # Unparseable numbers sort after every parseable one, but
        # deterministically among themselves rather than in model order.
        return (float("inf"), (), normalized)

    number, groups_str = match.groups()
    groups = _ORDER_GROUP_RE.findall(groups_str)
    group_key = tuple((len(g), g) for g in groups)
    return (int(number), group_key, "")
