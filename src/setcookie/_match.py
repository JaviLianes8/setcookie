"""Request URLs, default-path, domain-match and path-match (sections 5.1.2 to 5.1.4)."""

from __future__ import annotations

import ipaddress
from typing import TYPE_CHECKING, NamedTuple
from urllib.parse import urlsplit

from ._errors import CookieError

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
    """
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError as error:
        raise CookieError(f"the request URL is malformed: {url!r}") from error
    if not host:
        raise CookieError(f"the request URL has no host: {url!r}")
    try:
        canonical = host.rstrip(".").encode("idna").decode("ascii").lower()
        # A label that claims to be an A-label must decode (section 5.1.2 step 4).
        canonical.encode("ascii").decode("idna")
    except UnicodeError:
        raise CookieError(f"the request host cannot be canonicalized: {host!r}") from None
    return Request(canonical, parts.path, parts.scheme.lower() in _SECURE_SCHEMES)


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
