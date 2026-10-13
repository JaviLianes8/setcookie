"""Parse one Set-Cookie line with the user agent algorithm of section 5.6."""

from __future__ import annotations

from datetime import datetime

from ._chars import (
    MAX_ATTRIBUTE_OCTETS,
    MAX_PAIR_OCTETS,
    ascii_lower,
    has_forbidden_ctl,
    octets,
    trim,
)
from ._dates import parse_date
from ._errors import CookieError
from ._model import Cookie, SameSite
from ._strict import check_strict

_SAME_SITE: dict[str, SameSite] = {"lax": "Lax", "strict": "Strict", "none": "None"}


def parse(line: str, *, strict: bool = False) -> Cookie:
    """Decode one Set-Cookie line the way a user agent reads it.

    Raise CookieError when a user agent ignores the whole line: a control character
    other than HTAB, an empty name with an empty value, or a name and value longer than
    4096 octets together. Unknown or malformed attributes are skipped, never rejected.
    With ``strict=True`` the line must also follow the server grammar of section 4.1.1,
    and CookieError names the first rule it breaks.
    """
    if not isinstance(line, str):
        raise TypeError(f"expected str, got {type(line).__name__}")
    if strict:
        check_strict(line)
    if has_forbidden_ctl(line):
        raise CookieError(f"control character in the line: {line!r}")
    pair, separator, attributes = line.partition(";")
    if "=" in pair:
        raw_name, _, raw_value = pair.partition("=")
    else:
        raw_name, raw_value = "", pair
    name, value = trim(raw_name), trim(raw_value)
    if octets(name) + octets(value) > MAX_PAIR_OCTETS:
        raise CookieError("the name and value are longer than 4096 octets together")
    if not name and not value:
        raise CookieError(f"empty name and empty value: {line!r}")
    return _read_attributes(name, value, attributes.split(";") if separator else [])


def _read_attributes(name: str, value: str, avs: list[str]) -> Cookie:
    expires: datetime | None = None
    max_age: int | None = None
    domain: str | None = None
    path: str | None = None
    secure = http_only = partitioned = False
    same_site: SameSite | None = None
    extensions: list[tuple[str, str | None]] = []
    for av in avs:
        raw_key, equals, raw = av.partition("=")
        key, raw = trim(raw_key), trim(raw)
        if not key or octets(raw) > MAX_ATTRIBUTE_OCTETS:
            continue
        keyword = ascii_lower(key)
        if keyword == "expires":
            expires = parse_date(raw) or expires
        elif keyword == "max-age":
            max_age = _delta_seconds(raw, max_age)
        elif keyword == "domain":
            domain = ascii_lower(raw[1:] if raw.startswith(".") else raw) or None
        elif keyword == "path":
            path = raw if raw.startswith("/") else ""
        elif keyword == "secure":
            secure = True
        elif keyword == "httponly":
            http_only = True
        elif keyword == "partitioned":
            partitioned = True
        elif keyword == "samesite":
            same_site = _SAME_SITE.get(ascii_lower(raw))
        else:
            extensions.append((key, raw if equals else None))
    return Cookie(
        name=name,
        value=value,
        expires=expires,
        max_age=max_age,
        domain=domain,
        path=path,
        secure=secure,
        http_only=http_only,
        same_site=same_site,
        partitioned=partitioned,
        extensions=tuple(extensions),
    )


def _delta_seconds(raw: str, previous: int | None) -> int | None:
    """Section 5.6.2: DIGITs with an optional leading '-'; anything else keeps ``previous``."""
    digits = raw[1:] if raw.startswith("-") else raw
    if not digits or not all("0" <= char <= "9" for char in digits):
        return previous
    return int(raw)
