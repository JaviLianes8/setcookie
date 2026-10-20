"""Character classes, limits and small text helpers from the cookie grammar."""

from __future__ import annotations

WSP = " \t"
MAX_PAIR_OCTETS = 4096
MAX_ATTRIBUTE_OCTETS = 1024
MAX_AGE_LIMIT = 34560000  # 400 days in seconds, the cap of section 5.5

_ALNUM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
TCHAR = frozenset("!#$%&'*+-.^_`|~" + _ALNUM)
# Visible ASCII without DQUOTE, comma, semicolon and backslash.
COOKIE_OCTET = frozenset(chr(code) for code in range(0x21, 0x7F)) - frozenset('",;\\')
# Any CHAR except CTLs and semicolon.
AV_OCTET = frozenset(chr(code) for code in range(0x20, 0x7F)) - frozenset(";")
_UPPER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def first_ctl(text: str) -> str | None:
    """Name the first %x00-08, %x0A-1F or %x7F (a control other than HTAB), or None."""
    for index, char in enumerate(text):
        if (char < " " and char != "\t") or char == "\x7f":
            return f"U+{ord(char):04X} at index {index}"
    return None


def octets(text: str) -> int:
    """Length in octets once the text is put on the wire as UTF-8."""
    return len(text.encode("utf-8", "surrogatepass"))


def trim(text: str) -> str:
    """Remove leading and trailing WSP (space and horizontal tab) only."""
    return text.strip(WSP)


def ascii_lower(text: str) -> str:
    """Lower-case A to Z only, so no Unicode folding can turn a name into a keyword."""
    return text.translate(_UPPER)


def is_token(text: str) -> bool:
    """True for a non-empty HTTP token (RFC 9110 section 5.6.2)."""
    return bool(text) and all(char in TCHAR for char in text)


def is_hostname(text: str) -> bool:
    """True for an RFC 1034 subdomain as relaxed by RFC 1123 (labels may start with a digit)."""
    if not text or len(text) > 253 or not text.isascii():
        return False
    for label in text.split("."):
        if not 0 < len(label) <= 63 or label[0] == "-" or label[-1] == "-":
            return False
        if not all(char.isalnum() or char == "-" for char in label):
            return False
    return True


def shown(text: str, limit: int = 40) -> str:
    """The repr of ``text`` cut to ``limit`` characters, so an error message stays short."""
    if len(text) <= limit:
        return repr(text)
    return f"{text[:limit]!r}... ({len(text)} characters)"


def first_outside(
    text: str, allowed: frozenset[str], start: int = 0, end: int | None = None
) -> str | None:
    """Name the first character of ``text[start:end]`` not in ``allowed``, or None."""
    for index in range(start, len(text) if end is None else end):
        if text[index] not in allowed:
            return f"U+{ord(text[index]):04X} at index {index}"
    return None


def cookie_value_problem(text: str) -> str | None:
    """Where ``text`` leaves *cookie-octet (optionally inside one pair of DQUOTEs), or None."""
    if len(text) >= 2 and text[0] == '"' == text[-1]:
        return first_outside(text, COOKIE_OCTET, 1, len(text) - 1)
    return first_outside(text, COOKIE_OCTET)
