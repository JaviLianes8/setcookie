"""Typed representations of a Set-Cookie line and of a cookie a user agent stores."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from ._errors import type_error

SameSite = Literal["Lax", "Strict", "None"]


@dataclass(frozen=True)
class Cookie:
    """One Set-Cookie line decomposed into its name, value and attributes.

    When an attribute repeats, the last one wins as in a user agent: an unreadable Expires
    or Max-Age is skipped, while an empty Domain or an unknown SameSite value resets the
    earlier one. ``path`` is ``""`` when a Path attribute was given but was empty or
    relative, which tells the user agent to use the default path. ``extensions`` keeps
    unrecognised attributes in order as ``(name, value)``, with ``None`` for an attribute
    that had no ``=``.

    >>> from setcookie import parse
    >>> cookie = parse("sid=abc; Path=/app; Secure; Partitioned; x-flag")
    >>> cookie.path, cookie.secure, cookie.partitioned, cookie.extensions
    ('/app', True, True, (('x-flag', None),))
    >>> Cookie("sid", "abc", max_age=60, path="/", secure=True).header()
    'sid=abc; Max-Age=60; Path=/; Secure'
    """

    name: str
    value: str
    expires: datetime | None = None
    max_age: int | None = None
    domain: str | None = None
    path: str | None = None
    secure: bool = False
    http_only: bool = False
    same_site: SameSite | None = None
    partitioned: bool = False
    extensions: tuple[tuple[str, str | None], ...] = ()

    def header(self) -> str:
        """Render this cookie with `build`; raise CookieError when it breaks the grammar.

        >>> from setcookie import parse
        >>> parse("sid=abc;path=/;SECURE").header()
        'sid=abc; Path=/; Secure'
        >>> Cookie("", "nameless").header()
        Traceback (most recent call last):
        ...
        setcookie.CookieError: cookie name '' is not an HTTP token (empty, or nothing)
        """
        from ._build import build

        return build(
            self.name,
            self.value,
            expires=self.expires,
            max_age=self.max_age,
            domain=self.domain,
            path=self.path,
            secure=self.secure,
            http_only=self.http_only,
            same_site=self.same_site,
            partitioned=self.partitioned,
            extensions=self.extensions,
        )


@dataclass(frozen=True)
class StoredCookie:
    """A cookie as the storage model of section 5.7 records it.

    ``domain`` is the cookie's domain after matching against the request host;
    ``host_only`` is true when no Domain attribute widened it. ``expiry`` is ``None`` for
    a session cookie (``persistent`` false).

    >>> from datetime import datetime, timezone
    >>> from setcookie import receive
    >>> now = datetime(2026, 10, 13, tzinfo=timezone.utc)
    >>> stored = receive("sid=1; Max-Age=60", "https://example.com/app/login", now=now)
    >>> stored.domain, stored.host_only, stored.path, stored.persistent
    ('example.com', True, '/app', True)
    >>> print(stored.expiry)
    2026-10-13 00:01:00+00:00
    """

    name: str
    value: str
    domain: str
    path: str
    host_only: bool
    secure: bool
    http_only: bool
    same_site: SameSite | None
    partitioned: bool
    persistent: bool
    expiry: datetime | None

    def is_expired(self, now: datetime) -> bool:
        """True when the expiry time has been reached at ``now`` (an aware datetime).

        A naive ``now`` raises ValueError. A session cookie never expires here: it lasts
        until the session ends, which only the caller knows.

        >>> from datetime import datetime, timezone
        >>> from setcookie import receive
        >>> now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        >>> stored = receive("sid=1; Max-Age=60", "https://example.com/", now=now)
        >>> stored.is_expired(now), stored.is_expired(datetime(2026, 10, 14, tzinfo=timezone.utc))
        (False, True)
        """
        if not isinstance(now, datetime):
            raise type_error("now", "a datetime", now)
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be an aware datetime")
        return self.expiry is not None and self.expiry <= now

    def matches(self, url: str) -> bool:
        """True when a request to ``url`` would carry this cookie (domain, path, secure).

        SameSite and the request context are not checked. A malformed ``url`` raises
        CookieError.

        >>> from datetime import datetime, timezone
        >>> from setcookie import receive
        >>> now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        >>> line = "sid=1; Domain=example.com; Secure"
        >>> stored = receive(line, "https://www.example.com/", now=now)
        >>> stored.matches("https://shop.example.com/cart"), stored.matches("http://example.com/")
        (True, False)
        """
        from ._match import request_matches

        return request_matches(self, url)


Cookie.__module__ = "setcookie"
StoredCookie.__module__ = "setcookie"
