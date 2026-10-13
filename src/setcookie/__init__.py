"""Typed Set-Cookie codec: parse, validate and build one Set-Cookie line, and store it."""

from __future__ import annotations

from ._build import build, expire
from ._dates import parse_date
from ._errors import CookieError
from ._model import Cookie, SameSite, StoredCookie
from ._parse import parse
from ._store import receive

__version__ = "0.2.0"

__all__ = [
    "Cookie",
    "CookieError",
    "SameSite",
    "StoredCookie",
    "build",
    "expire",
    "parse",
    "parse_date",
    "receive",
]
