"""Build one Set-Cookie line that follows the server grammar of section 4.1.1."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import NoReturn

from ._chars import (
    MAX_ATTRIBUTE_OCTETS,
    MAX_PAIR_OCTETS,
    WSP,
    ascii_lower,
    is_av_text,
    is_cookie_value,
    is_hostname,
    is_token,
    octets,
)
from ._dates import format_http_date
from ._errors import CookieError
from ._model import SameSite
from ._rules import prefix_problem, secure_problem
from ._strict import check_strict

_SAME_SITE_VALUES = ("Lax", "Strict", "None")
_KNOWN = frozenset(
    {"expires", "max-age", "domain", "path", "secure", "httponly", "samesite", "partitioned"}
)
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def build(
    name: str,
    value: str,
    *,
    expires: datetime | None = None,
    max_age: int | None = None,
    domain: str | None = None,
    path: str | None = "/",
    secure: bool = False,
    http_only: bool = False,
    same_site: SameSite | None = None,
    partitioned: bool = False,
    extensions: Iterable[tuple[str, str | None]] = (),
) -> str:
    """Assemble one Set-Cookie line; raise CookieError for anything unsafe or ignored.

    Every part is checked on its own before it is joined, so no argument can end the
    line, start another attribute or inject a header. Prefix rules, the Secure
    requirement of SameSite=None and Partitioned, and the size limits are enforced.
    """
    _check_pair(name, value)
    parts = [f"{name}={value}"]
    if expires is not None:
        parts.append(f"Expires={_expires(expires)}")
    if max_age is not None:
        if isinstance(max_age, bool) or not isinstance(max_age, int) or max_age < 1:
            _fail(f"max_age must be a positive int, got {max_age!r}; use expire() to delete")
        parts.append(f"Max-Age={max_age}")
    if domain is not None:
        if not is_hostname(domain):
            _fail(f"domain {domain!r} is not a host name (no leading dot, no port)")
        parts.append(f"Domain={domain}")
    if path is not None:
        if path and not path.startswith("/"):
            _fail(f"path {path!r} must be empty or start with '/'")
        _check_attribute_value("path", path)
        parts.append(f"Path={path}")
    parts.extend(flag for flag, on in (("Secure", secure), ("HttpOnly", http_only)) if on)
    if same_site is not None:
        if same_site not in _SAME_SITE_VALUES:
            _fail(f"same_site must be one of {_SAME_SITE_VALUES}, got {same_site!r}")
        parts.append(f"SameSite={same_site}")
    if partitioned:
        parts.append("Partitioned")
    parts.extend(_extension(key, text) for key, text in extensions)
    problem = prefix_problem(
        name, secure=secure, has_domain=domain is not None, path=path
    ) or secure_problem(same_site=same_site, partitioned=partitioned, secure=secure)
    if problem:
        _fail(problem)
    header = "; ".join(parts)
    check_strict(header)
    return header


def expire(
    name: str,
    *,
    domain: str | None = None,
    path: str | None = "/",
    secure: bool = False,
    http_only: bool = False,
    same_site: SameSite | None = None,
    partitioned: bool = False,
) -> str:
    """Build a line that deletes the cookie: an empty value and an Expires in 1970.

    Pass the same name, Domain and Path the cookie was set with; prefixed names still
    need their Secure, Domain and Path rules.
    """
    return build(
        name,
        "",
        expires=_EPOCH,
        domain=domain,
        path=path,
        secure=secure,
        http_only=http_only,
        same_site=same_site,
        partitioned=partitioned,
    )


def _check_pair(name: str, value: str) -> None:
    if not isinstance(name, str) or not is_token(name):
        _fail(f"cookie name {name!r} is not an HTTP token")
    if not isinstance(value, str) or not is_cookie_value(value):
        _fail(f"cookie value {value!r} has characters outside cookie-octet; encode it first")
    if octets(name) + octets(value) > MAX_PAIR_OCTETS:
        _fail("the name and value are longer than 4096 octets together")


def _expires(moment: datetime) -> str:
    if not isinstance(moment, datetime):
        _fail(f"expires must be a datetime, got {type(moment).__name__}")
    text = format_http_date(moment)
    if int(text[12:16]) < 1601:
        _fail("expires before the year 1601 is ignored by user agents")
    return text


def _extension(key: str, text: str | None) -> str:
    if not key or key != key.strip(WSP) or "=" in key or not is_av_text(key):
        _fail(f"extension name {key!r} is not a valid attribute name")
    if ascii_lower(key) in _KNOWN:
        _fail(f"extension {key!r} would be read as a standard attribute; use its argument")
    if text is None:
        return key
    if text != text.strip(WSP):
        _fail(f"extension value {text!r} has leading or trailing whitespace")
    _check_attribute_value(key, text)
    return f"{key}={text}"


def _check_attribute_value(label: str, text: str) -> None:
    if not is_av_text(text):
        _fail(f"{label} value {text!r} has control characters or ';'")
    if octets(text) > MAX_ATTRIBUTE_OCTETS:
        _fail(f"{label} value is longer than 1024 octets")


def _fail(reason: str) -> NoReturn:
    raise CookieError(reason)
