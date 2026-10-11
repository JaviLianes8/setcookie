"""Typed single-line Set-Cookie codec: parse and build one Set-Cookie header per RFC 6265."""

from __future__ import annotations

from ._build import build
from ._errors import CookieError
from ._model import Cookie, SameSite
from ._parse import parse

__version__ = "0.1.0"

__all__ = ["Cookie", "CookieError", "SameSite", "build", "parse"]
