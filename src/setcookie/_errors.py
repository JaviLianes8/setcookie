"""Errors raised by the codec."""

from __future__ import annotations


class CookieError(ValueError):
    """A Set-Cookie line a user agent ignores, breaks the grammar, or cannot be built safely.

    It is a ``ValueError``. The message names the rule that was broken; it never quotes a
    cookie value and cuts any other quoted text to 40 characters, so it is safe to log.
    Arguments of the wrong type raise ``TypeError`` instead.

    >>> from setcookie import CookieError, parse
    >>> try:
    ...     parse("sid=a b", strict=True)
    ... except CookieError as error:
    ...     print(error)
    strict: the cookie-value has U+0020 at index 1, outside cookie-octet
    >>> issubclass(CookieError, ValueError)
    True
    """


CookieError.__module__ = "setcookie"


def type_error(label: str, expected: str, value: object) -> TypeError:
    """A TypeError naming the argument, what it must be, and the type it got."""
    return TypeError(f"{label} must be {expected}, got {type(value).__name__}")
