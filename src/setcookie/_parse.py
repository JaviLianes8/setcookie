"""Parse a single Set-Cookie header line into a typed Cookie."""

from __future__ import annotations

from datetime import datetime

from ._dates import parse_http_date
from ._errors import CookieError
from ._model import Cookie, SameSite

_SAME_SITE: dict[str, SameSite] = {"lax": "Lax", "strict": "Strict", "none": "None"}


def parse(line: str) -> Cookie:
    """Decode one Set-Cookie line; raise CookieError when it has no name=value pair.

    Attribute names are matched case-insensitively and unrecognised or malformed
    attributes are ignored rather than rejected, matching how clients read the header.
    """
    segments = line.split(";")
    pair = segments[0].strip()
    if "=" not in pair:
        raise CookieError(f"missing name=value pair: {line!r}")
    raw_name, _, raw_value = pair.partition("=")
    name = raw_name.strip()
    if not name:
        raise CookieError(f"empty cookie name: {line!r}")

    expires: datetime | None = None
    max_age: int | None = None
    domain: str | None = None
    path: str | None = None
    secure = False
    http_only = False
    same_site: SameSite | None = None

    for segment in segments[1:]:
        key, _, raw = segment.partition("=")
        key = key.strip().lower()
        raw = raw.strip()
        if key == "expires":
            expires = parse_http_date(raw)
        elif key == "max-age":
            max_age = _to_int(raw)
        elif key == "domain":
            domain = raw or None
        elif key == "path":
            path = raw or None
        elif key == "secure":
            secure = True
        elif key == "httponly":
            http_only = True
        elif key == "samesite":
            same_site = _SAME_SITE.get(raw.lower())

    return Cookie(
        name=name,
        value=raw_value.strip(),
        expires=expires,
        max_age=max_age,
        domain=domain,
        path=path,
        secure=secure,
        http_only=http_only,
        same_site=same_site,
    )


def _to_int(raw: str) -> int | None:
    try:
        return int(raw)
    except ValueError:
        return None
