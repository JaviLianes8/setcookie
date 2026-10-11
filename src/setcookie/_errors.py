"""Errors raised by the codec."""

from __future__ import annotations


class CookieError(ValueError):
    """Raised when a Set-Cookie line has no usable name and value pair."""
