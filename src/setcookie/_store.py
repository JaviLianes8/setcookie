"""The storage model of section 5.7 for one received cookie."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from ._chars import MAX_AGE_LIMIT, ascii_lower, shown
from ._errors import CookieError, type_error
from ._match import default_path, domain_match
from ._model import EARLIEST, Cookie, StoredCookie
from ._parse import parse
from ._rules import prefix_problem, secure_problem
from ._url import request_of

_LATEST = datetime.max.replace(tzinfo=timezone.utc)
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
    cookies may be set. ``is_public_suffix`` enables the public suffix check of step 9: it
    is called with the Domain attribute lower-cased (A to Z only), without its leading dot
    and without a trailing dot, so ``Domain=.CO.UK.`` asks about ``"co.uk"``.
    Rules that need the existing cookie store (steps 16, 23 and 24) are left to the caller.
    Arguments of the wrong type raise TypeError and a naive ``now`` raises ValueError.

    >>> from datetime import datetime, timezone
    >>> now = datetime(2026, 10, 13, tzinfo=timezone.utc)
    >>> stored = receive("sid=1; Domain=example.com", "https://www.example.com/app/x", now=now)
    >>> stored.domain, stored.host_only, stored.path, stored.persistent
    ('example.com', False, '/app', False)
    >>> receive("sid=1; Secure", "http://www.example.com/", now=now)
    Traceback (most recent call last):
    ...
    setcookie.CookieError: a Secure cookie cannot be set from an insecure URL
    """
    if not isinstance(line, str):
        raise type_error("line", "a str", line)
    if not isinstance(url, str):
        raise type_error("url", "a str", url)
    if not isinstance(now, datetime):
        raise type_error("now", "a datetime", now)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be an aware datetime")
    if not isinstance(cross_site, bool):
        raise type_error("cross_site", "a bool", cross_site)
    if is_public_suffix is not None and not callable(is_public_suffix):
        raise type_error("is_public_suffix", "a callable or None", is_public_suffix)
    cookie = parse(str.__str__(line))
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
        raise CookieError(f"the Domain attribute {shown(attribute)} is not ASCII")
    # Registry lookups ignore a trailing dot, as browsers' do: co.uk. is the suffix co.uk.
    bare = attribute[:-1] if attribute.endswith(".") else attribute
    if bare and is_public_suffix is not None and is_public_suffix(bare):
        if attribute != host:
            raise CookieError(f"the Domain attribute {shown(attribute)} is a public suffix")
        attribute = ""
    if not attribute:
        return host, True
    if not domain_match(host, attribute):
        raise CookieError(f"the host {shown(host)} does not domain-match {shown(attribute)}")
    return attribute, False


def _expiry(cookie: Cookie, now: datetime) -> datetime | None:
    if cookie.max_age is not None:
        if cookie.max_age <= 0:
            return EARLIEST
        return _later(now, timedelta(seconds=min(cookie.max_age, MAX_AGE_LIMIT)))
    if cookie.expires is not None:
        return min(cookie.expires, _later(now, _LIMIT))
    return None


def _later(now: datetime, delta: timedelta) -> datetime:
    """``now + delta``, or the latest representable time when that overflows."""
    try:
        return now + delta
    except OverflowError:
        return _LATEST


receive.__module__ = "setcookie"
