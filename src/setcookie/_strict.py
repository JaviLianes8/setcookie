"""Strict mode: check a Set-Cookie line against the server grammar of section 4.1.1."""

from __future__ import annotations

import re
from typing import NoReturn

from ._chars import (
    AV_OCTET,
    MAX_ATTRIBUTE_OCTETS,
    MAX_PAIR_OCTETS,
    WSP,
    ascii_lower,
    cookie_value_problem,
    first_outside,
    is_hostname,
    is_token,
    octets,
    shown,
)
from ._dates import fixdate_problem
from ._errors import CookieError
from ._rules import prefix_problem, secure_problem

_FLAGS = frozenset({"secure", "httponly", "partitioned"})
_VALUED = frozenset({"expires", "max-age", "domain", "path", "samesite"})
_MAX_AGE = re.compile(r"[1-9][0-9]*")
_SAME_SITE = frozenset({"strict", "lax", "none"})


def check_strict(line: str) -> None:
    """Raise CookieError naming the first rule of the server grammar the line breaks."""
    if line != line.rstrip(WSP):
        _fail("trailing whitespace")
    pair, *avs = line.split(";")
    raw_name, equals, raw_value = pair.partition("=")
    if not equals:
        _fail("the cookie-pair has no '='")
    name, value = raw_name.strip(WSP), raw_value.strip(WSP)
    if not is_token(name):
        _fail(f"the cookie-name {shown(name)} is not a token")
    problem = cookie_value_problem(value)
    if problem:
        _fail(f"the cookie-value has {problem}, outside cookie-octet")
    if octets(name) + octets(value) > MAX_PAIR_OCTETS:
        _fail("the name and value are longer than 4096 octets together")
    seen: dict[str, str] = {}
    for av in avs:
        keyword, text = _attribute(av.strip(WSP))
        if keyword in seen:
            _fail(f"the {keyword} attribute appears twice")
        seen[keyword] = text
    _check_semantics(name, seen)


def _attribute(av: str) -> tuple[str, str]:
    """Validate one cookie-av; return its lower-cased name and its value."""
    if not av:
        _fail("empty attribute")
    raw_key, equals, raw = av.partition("=")
    keyword, text = ascii_lower(raw_key.strip(WSP)), raw.strip(WSP)
    if octets(text) > MAX_ATTRIBUTE_OCTETS:
        _fail(f"the {shown(raw_key.strip(WSP))} value is longer than 1024 octets")
    if keyword in _FLAGS:
        if equals:
            _fail(f"the {keyword} attribute takes no value")
    elif keyword in _VALUED:
        if not equals:
            _fail(f"the {keyword} attribute needs a value")
        _check_value(keyword, text)
    elif problem := first_outside(av, AV_OCTET):
        _fail(f"the attribute {shown(av)} has {problem}, outside av-octet")
    return keyword, text


def _check_value(keyword: str, text: str) -> None:
    if keyword == "expires" and (problem := fixdate_problem(text)):
        _fail(f"Expires={shown(text)} {problem}")
    if keyword == "max-age" and not _MAX_AGE.fullmatch(text):
        _fail(f"Max-Age={shown(text)} is not a non-zero-digit followed by DIGITs")
    if keyword == "domain" and not is_hostname(text):
        _fail(f"Domain={shown(text)} is not a host name")
    if keyword == "path" and (problem := first_outside(text, AV_OCTET)):
        _fail(f"Path={shown(text)} has {problem}, outside av-octet")
    if keyword == "samesite" and ascii_lower(text) not in _SAME_SITE:
        _fail(f"SameSite={shown(text)} is not Strict, Lax or None")


def _check_semantics(name: str, attributes: dict[str, str]) -> None:
    secure = "secure" in attributes
    same_site = attributes.get("samesite")
    problem = prefix_problem(
        name, secure=secure, has_domain="domain" in attributes, path=attributes.get("path")
    ) or secure_problem(
        same_site="None" if same_site is not None and ascii_lower(same_site) == "none" else None,
        partitioned="partitioned" in attributes,
        secure=secure,
    )
    if problem:
        _fail(problem)


def _fail(reason: str) -> NoReturn:
    raise CookieError(f"strict: {reason}")
