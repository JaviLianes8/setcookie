"""The storage model of section 5.7 for one received cookie."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from ._chars import MAX_AGE_LIMIT, ascii_lower
from ._errors import CookieError
from ._match import default_path, domain_match, request_of
from ._model import Cookie, StoredCookie
from ._parse import parse
from ._rules import prefix_problem, secure_problem

_EARLIEST = datetime.min.replace(tzinfo=timezone.utc)
_LIMIT = timedelta(seconds=MAX_AGE_LIMIT)


def receive(
    line: str,
    url: str,
    *,
    now: datetime,
    cross_site: bool = False,
    is_public_suffix: Callable[[str], bool] | None = None,
) -> StoredCookie:
    """Run the storage model for a Set-Cookie line received from ``url`` at ``now``.

    Return the cookie a user agent would store, or raise CookieError naming the rule that
    makes it ignore the line. ``now`` must be an aware datetime. ``cross_site`` marks a
    cross-site request that is not a top-level navigation, where only SameSite=None
    cookies may be set. ``is_public_suffix`` enables the public suffix check of step 9.
    Rules that need the existing cookie store (steps 16, 23 and 24) are left to the caller.
    """
    if now.tzinfo is None:
        raise ValueError("now must be an aware datetime")
    cookie = parse(line)
    request = request_of(url)
    domain, host_only = _domain(cookie, request.host, is_public_suffix)
    path = cookie.path or default_path(request.path)
    if cookie.secure and not request.secure:
        raise CookieError("a Secure cookie cannot be set from an insecure URL")
    if cross_site and cookie.same_site != "None":
        raise CookieError("a cross-site request can only set a SameSite=None cookie")
    problem = secure_problem(
        same_site=cookie.same_site, partitioned=cookie.partitioned, secure=cookie.secure
    ) or prefix_problem(
        cookie.name,
        secure=cookie.secure,
        has_domain=not host_only,
        path=path if cookie.path is not None else None,
    )
    if problem:
        raise CookieError(problem)
    if not cookie.name and ascii_lower(cookie.value).startswith(("__secure-", "__host-")):
        raise CookieError("a nameless cookie cannot carry a prefixed value")
    expiry = _expiry(cookie, now)
    return StoredCookie(
        name=cookie.name,
        value=cookie.value,
        domain=domain,
        path=path,
        host_only=host_only,
        secure=cookie.secure,
        http_only=cookie.http_only,
        same_site=cookie.same_site,
        partitioned=cookie.partitioned,
        persistent=expiry is not None,
        expiry=expiry,
    )


def _domain(
    cookie: Cookie, host: str, is_public_suffix: Callable[[str], bool] | None
) -> tuple[str, bool]:
    attribute = cookie.domain or ""
    if not attribute.isascii():
        raise CookieError(f"the Domain attribute {attribute!r} is not ASCII")
    if attribute and is_public_suffix is not None and is_public_suffix(attribute):
        if attribute != host:
            raise CookieError(f"the Domain attribute {attribute!r} is a public suffix")
        attribute = ""
    if not attribute:
        return host, True
    if not domain_match(host, attribute):
        raise CookieError(f"the host {host!r} does not domain-match {attribute!r}")
    return attribute, False


def _expiry(cookie: Cookie, now: datetime) -> datetime | None:
    if cookie.max_age is not None:
        if cookie.max_age <= 0:
            return _EARLIEST
        return now + timedelta(seconds=min(cookie.max_age, MAX_AGE_LIMIT))
    if cookie.expires is not None:
        return min(cookie.expires, now + _LIMIT)
    return None
