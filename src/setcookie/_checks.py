"""Argument checks of the builder: types first, then the server grammar of section 4.1.1."""

from __future__ import annotations

from datetime import datetime
from typing import NoReturn, TypeVar, cast

from ._chars import (
    AV_OCTET,
    MAX_ATTRIBUTE_OCTETS,
    MAX_PAIR_OCTETS,
    TCHAR,
    WSP,
    ascii_lower,
    cookie_value_problem,
    first_outside,
    is_hostname,
    is_token,
    octets,
    shown,
)
from ._dates import format_http_date
from ._errors import CookieError, type_error

_SAME_SITE_VALUES = ("Lax", "Strict", "None")
_KNOWN = frozenset(
    {"expires", "max-age", "domain", "path", "secure", "httponly", "samesite", "partitioned"}
)
_BIG = 10**MAX_ATTRIBUTE_OCTETS  # more digits than an attribute value may hold
_T = TypeVar("_T")


def exact(value: _T) -> _T:
    """The plain str or int a subclass holds, so an Enum member or a __format__ cannot lie."""
    if isinstance(value, str):
        return cast(_T, str.__str__(value))
    if isinstance(value, int) and not isinstance(value, bool):
        return cast(_T, int.__int__(value))
    return value


def fail(reason: str) -> NoReturn:
    raise CookieError(reason)


def check_flags(**flags: object) -> None:
    for label, flag in flags.items():
        if not isinstance(flag, bool):
            raise type_error(label, "a bool", flag)


def check_optional_str(label: str, value: object) -> None:
    if value is not None and not isinstance(value, str):
        raise type_error(label, "a str or None", value)


def check_pair(name: object, value: object) -> None:
    if not isinstance(name, str):
        raise type_error("name", "a str", name)
    if not isinstance(value, str):
        raise type_error("value", "a str", value)
    if not is_token(name):
        where = first_outside(name, TCHAR) or "nothing"
        fail(f"cookie name {shown(name)} is not an HTTP token (empty, or {where})")
    problem = cookie_value_problem(value)
    if problem:
        fail(f"cookie value has {problem}, outside cookie-octet; encode it first")
    if octets(name) + octets(value) > MAX_PAIR_OCTETS:
        fail("the name and value are longer than 4096 octets together")


def check_max_age(max_age: object) -> int:
    if isinstance(max_age, bool) or not isinstance(max_age, int):
        raise type_error("max_age", "an int or None", max_age)
    if not 0 < max_age < _BIG:
        fail("max_age must be a positive int below 10**1024; use expire() to delete")
    return max_age


def expires_text(moment: object) -> str:
    if not isinstance(moment, datetime):
        raise type_error("expires", "a datetime or None", moment)
    try:
        text = format_http_date(moment)
    except OverflowError:
        fail("expires is outside the range of representable UTC dates")
    if int(text[12:16]) < 1601:
        fail("expires before the year 1601 is ignored by user agents")
    return text


def check_domain(domain: str) -> None:
    if not is_hostname(domain):
        fail(f"domain {shown(domain)} is not a host name (no leading dot, no port)")


def check_path(path: str) -> None:
    if path and not path.startswith("/"):
        fail(f"path {shown(path)} must be empty or start with '/'")
    if path != path.strip(WSP):
        fail(f"path {shown(path)} has leading or trailing whitespace")
    check_attribute_value("path", path)


def check_same_site(same_site: object) -> None:
    if not isinstance(same_site, str):
        raise type_error("same_site", "a str or None", same_site)
    if same_site not in _SAME_SITE_VALUES:
        fail(f"same_site must be one of {_SAME_SITE_VALUES}, got {shown(same_site)}")


def extension_text(item: object) -> str:
    if not isinstance(item, tuple) or len(item) != 2:
        raise type_error("each extension", "a (name, value) tuple", item)
    key, text = exact(item[0]), exact(item[1])
    if not isinstance(key, str):
        raise type_error("an extension name", "a str", key)
    if not isinstance(text, (str, type(None))):
        raise type_error("an extension value", "a str or None", text)
    if not key or key != key.strip(WSP) or "=" in key or first_outside(key, AV_OCTET):
        fail(f"extension name {shown(key)} is not a valid attribute name")
    if ascii_lower(key) in _KNOWN:
        fail(f"extension {shown(key)} would be read as a standard attribute; use its argument")
    if text is None:
        return key
    if text != text.strip(WSP):
        fail(f"extension {shown(key)} has a value with leading or trailing whitespace")
    check_attribute_value(f"extension {shown(key)}", text)
    return f"{key}={text}"


def check_attribute_value(label: str, text: str) -> None:
    problem = first_outside(text, AV_OCTET)
    if problem:
        fail(f"{label} value has {problem}, outside av-octet (control, non-ASCII or ';')")
    if octets(text) > MAX_ATTRIBUTE_OCTETS:
        fail(f"{label} value is longer than 1024 octets")
