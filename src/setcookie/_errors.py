"""Errors raised by the codec."""

from __future__ import annotations


class CookieError(ValueError):
    """A Set-Cookie line a user agent ignores, breaks the grammar, or cannot be built safely."""
