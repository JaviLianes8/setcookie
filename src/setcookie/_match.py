"""Request URLs, default-path, domain-match and path-match (sections 5.1.2 to 5.1.4)."""

from __future__ import annotations

import ipaddress
from typing import TYPE_CHECKING, NamedTuple
from urllib.parse import urlsplit

from ._chars import shown
from ._errors import CookieError, type_error

if TYPE_CHECKING:
    from ._model import StoredCookie

_SECURE_SCHEMES = frozenset({"https", "wss"})


class Request(NamedTuple):
    host: str
    path: str
    secure: bool


def request_of(url: str) -> Request:
    """Split a request URL into its canonical host, path and whether it is secure.

    Non-ASCII hosts go through the standard library's IDNA 2003 codec, which maps a few
    characters (such as sharp s) differently from the IDNA 2008 rules of section 5.1.2.
    A trailing dot is kept, so ``example.com.`` is a host of its own as in browsers, and a
    host whose last label is a number is read as an IPv4 address the way the WHATWG URL
    parser reads it (``127.1`` is ``127.0.0.1``).
    """
    if not isinstance(url, str):
        raise type_error("url", "a str", url)
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError as error:
        raise CookieError("the request URL is malformed") from error
    if not host:
        raise CookieError("the request URL has no host")
    try:
        canonical = host.encode("idna").decode("ascii").lower()
        # A label that claims to be an A-label must decode (section 5.1.2 step 4); a huge
        # one makes the punycode decoder raise OverflowError on some Python versions.
        canonical.encode("ascii").decode("idna")
        canonical = _ipv4(canonical) or canonical
    except (ValueError, OverflowError):
        raise CookieError(f"the request host cannot be canonicalized: {shown(host)}") from None
    return Request(canonical, parts.path, parts.scheme.lower() in _SECURE_SCHEMES)


def _ipv4_number(part: str) -> int | None:
    base = 10
    if part[:2] == "0x":
        base, part = 16, part[2:]
    elif len(part) > 1 and part[0] == "0":
        base, part = 8, part[1:]
    if not part:
        return 0
    if part.strip("0123456789abcdef"[:base]):
        return None
    return int(part, base)


def _ipv4(host: str) -> str | None:
    """The WHATWG URL host parser: a host that ends in a number is an IPv4 address."""
    labels = host.split(".")
    if len(labels) > 1 and not labels[-1]:
        labels.pop()
    last = labels[-1]
    if ":" in host or not last or (last.strip("0123456789") and _ipv4_number(last) is None):
        return None
    numbers = [_ipv4_number(label) if label else None for label in labels]
    if len(numbers) > 4 or None in numbers:
        raise ValueError("not an IPv4 address")
    *head, tail = (number for number in numbers if number is not None)
    if any(number > 255 for number in head) or tail >= 256 ** (5 - len(numbers)):
        raise ValueError("an IPv4 part is out of range")
    for index, number in enumerate(head):
        tail += number << (8 * (3 - index))
    return str(ipaddress.IPv4Address(tail))


def is_ip_address(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def domain_match(host: str, domain: str) -> bool:
    """Section 5.1.3: identical, or a host name ending in '.' + domain."""
    if host == domain:
        return True
    return host.endswith("." + domain) and not is_ip_address(host)


def default_path(uri_path: str) -> str:
    """Section 5.1.4: the directory of the request path, '/' when there is none."""
    if not uri_path.startswith("/") or uri_path.count("/") <= 1:
        return "/"
    return uri_path[: uri_path.rindex("/")]


def path_match(request_path: str, cookie_path: str) -> bool:
    """Section 5.1.4: identical, or a prefix that ends at a '/' boundary."""
    if request_path == cookie_path:
        return True
    if not request_path.startswith(cookie_path):
        return False
    return cookie_path.endswith("/") or request_path[len(cookie_path)] == "/"


def request_matches(cookie: StoredCookie, url: str) -> bool:
    request = request_of(url)
    if cookie.host_only:
        if request.host != cookie.domain:
            return False
    elif not domain_match(request.host, cookie.domain):
        return False
    if not path_match(request.path or "/", cookie.path):
        return False
    return request.secure or not cookie.secure
