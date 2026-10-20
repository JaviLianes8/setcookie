"""Default-path, domain-match and path-match (sections 5.1.3 and 5.1.4)."""

from __future__ import annotations

import ipaddress
from typing import TYPE_CHECKING

from ._url import request_of

if TYPE_CHECKING:
    from ._model import StoredCookie


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
