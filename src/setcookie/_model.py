"""Typed representations of a Set-Cookie line and of a cookie a user agent stores."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

SameSite = Literal["Lax", "Strict", "None"]


@dataclass(frozen=True)
class Cookie:
    """One Set-Cookie line decomposed into its name, value and attributes.

    When an attribute repeats, the last valid one wins, as in a user agent. ``path`` is
    ``""`` when a Path attribute was given but was empty or relative, which tells the
    user agent to use the default path. ``extensions`` keeps unrecognised attributes in
    order as ``(name, value)``, with ``None`` for an attribute that had no ``=``.
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
        """Render this cookie with `build`; raise CookieError when it breaks the grammar."""
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
        """True when the expiry time has been reached at ``now`` (an aware datetime)."""
        return self.expiry is not None and self.expiry <= now

    def matches(self, url: str) -> bool:
        """True when a request to ``url`` would carry this cookie (domain, path, secure)."""
        from ._match import request_matches

        return request_matches(self, url)
