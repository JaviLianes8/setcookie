"""Build one Set-Cookie line that follows the server grammar of section 4.1.1."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone

from ._checks import (
    check_domain,
    check_flags,
    check_max_age,
    check_optional_str,
    check_pair,
    check_path,
    check_same_site,
    expires_text,
    extension_text,
    fail,
)
from ._errors import type_error
from ._model import SameSite
from ._rules import prefix_problem, secure_problem
from ._strict import check_strict

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
    A naive ``expires`` is taken to be UTC, not local time. ``path=None`` leaves the
    Path attribute out. An argument of the wrong type raises TypeError.

    >>> build("sid", "a1b2", max_age=3600, secure=True, http_only=True, same_site="Lax")
    'sid=a1b2; Max-Age=3600; Path=/; Secure; HttpOnly; SameSite=Lax'
    >>> build("theme", "dark", path=None, extensions=[("Priority", "High")])
    'theme=dark; Priority=High'
    >>> build("sid", "a\\r\\nSet-Cookie: admin=1")
    Traceback (most recent call last):
    ...
    setcookie.CookieError: cookie value has U+000D at index 1, outside cookie-octet; encode it first
    """
    check_pair(name, value)
    check_flags(secure=secure, http_only=http_only, partitioned=partitioned)
    for label, text in (("domain", domain), ("path", path)):
        check_optional_str(label, text)
    parts = [f"{name}={value}"]
    if expires is not None:
        parts.append(f"Expires={expires_text(expires)}")
    if max_age is not None:
        parts.append(f"Max-Age={check_max_age(max_age)}")
    if domain is not None:
        check_domain(domain)
        parts.append(f"Domain={domain}")
    if path is not None:
        check_path(path)
        parts.append(f"Path={path}")
    parts.extend(flag for flag, on in (("Secure", secure), ("HttpOnly", http_only)) if on)
    if same_site is not None:
        check_same_site(same_site)
        parts.append(f"SameSite={same_site}")
    if partitioned:
        parts.append("Partitioned")
    if isinstance(extensions, (str, bytes)):
        raise type_error("extensions", "an iterable of (name, value) tuples", extensions)
    parts.extend(extension_text(item) for item in extensions)
    problem = prefix_problem(
        name, secure=secure, has_domain=domain is not None, path=path
    ) or secure_problem(same_site=same_site, partitioned=partitioned, secure=secure)
    if problem:
        fail(problem)
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

    >>> expire("sid")
    'sid=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/'
    >>> expire("__Host-sid", secure=True)
    '__Host-sid=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/; Secure'
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
