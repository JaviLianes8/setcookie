"""Build a single Set-Cookie header line."""

from __future__ import annotations

from datetime import datetime

from ._dates import format_http_date
from ._model import SameSite


def build(
    name: str,
    value: str,
    *,
    max_age: int | None = None,
    domain: str | None = None,
    path: str | None = "/",
    secure: bool = False,
    http_only: bool = False,
    same_site: SameSite | None = None,
    expires: datetime | None = None,
) -> str:
    """Assemble one Set-Cookie line from a name, value and the given attributes."""
    if not name:
        raise ValueError("cookie name must not be empty")
    parts = [f"{name}={value}"]
    if expires is not None:
        parts.append(f"Expires={format_http_date(expires)}")
    if max_age is not None:
        parts.append(f"Max-Age={max_age}")
    if domain:
        parts.append(f"Domain={domain}")
    if path:
        parts.append(f"Path={path}")
    if secure:
        parts.append("Secure")
    if http_only:
        parts.append("HttpOnly")
    if same_site is not None:
        parts.append(f"SameSite={same_site}")
    return "; ".join(parts)
