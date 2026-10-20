"""Hostile input: every entry point stays linear in the size of what it reads."""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable
from datetime import datetime, timezone

import pytest

from setcookie import CookieError, build, parse, parse_date, receive

NOW = datetime(2026, 10, 20, tzinfo=timezone.utc)
SHAPES: dict[str, Callable[[int], str]] = {
    "semicolons": lambda n: "a=b" + ";" * n,
    "equals": lambda n: "a" + "=" * n,
    "attributes": lambda n: "a=b" + "; x=y" * (n // 5),
    "repeated expires": lambda n: "a=b" + "; Expires=1:1:1 1 Jan 1970" * (n // 27),
    "date tokens": lambda n: "a=b; Expires=" + "1:1:1 " * (n // 6),
    "digits": lambda n: "a=b; Max-Age=" + "9" * n,
    "whitespace": lambda n: "a" + " \t" * (n // 2) + "=b",
    "quotes": lambda n: 'a="' + '"' * n,
    "dots": lambda n: "a=b; Domain=" + "." * n,
    "flags": lambda n: "a=b" + "; Secure" * (n // 8),
    "unicode": lambda n: "a=" + "\u00e9" * n,
}


def _seconds(call: Callable[[], object]) -> float:
    best = float("inf")
    for _ in range(3):
        start = time.perf_counter()
        with contextlib.suppress(CookieError):
            call()
        best = min(best, time.perf_counter() - start)
    return best


def _linear(make: Callable[[int], Callable[[], object]], size: int = 50000) -> None:
    # Eight times the input costs eight times the time when linear and 64 when quadratic.
    # The bound sits between the two, and a measurement spoiled by a busy machine is
    # taken again, so load on other cores cannot fail a linear entry point.
    timings = []
    for _ in range(3):
        small, large = _seconds(make(size)), _seconds(make(size * 8))
        if large < max(small, 0.005) * 24:
            return
        timings.append((small, large))
    raise AssertionError(f"grows faster than linear: {timings}")


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_parse_is_linear(shape: str) -> None:
    _linear(lambda n: lambda: parse(SHAPES[shape](n)))


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_strict_parse_is_linear(shape: str) -> None:
    _linear(lambda n: lambda: parse(SHAPES[shape](n), strict=True))


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_receive_is_linear(shape: str) -> None:
    _linear(lambda n: lambda: receive(SHAPES[shape](n), "https://a.example/b/c", now=NOW))


@pytest.mark.parametrize("text", ["1:1:1 ", "1 ", "a", " ", "999999", "Jan "])
def test_parse_date_is_linear(text: str) -> None:
    _linear(lambda n: lambda: parse_date(text * (n // len(text))))


def test_build_is_linear() -> None:
    _linear(lambda n: lambda: build("a", "b" * n))
    _linear(lambda n: lambda: build("a", "b", extensions=[("x", None)] * (n // 4)))
    _linear(lambda n: lambda: build("a", "b", domain="a." * (n // 2) + "b"))


def test_a_long_url_is_linear() -> None:
    _linear(lambda n: lambda: receive("a=b", "https://h.example/" + "a/" * n, now=NOW))
    _linear(lambda n: lambda: receive("a=b", "https://" + "a." * n + "example/", now=NOW))


def test_ten_megabytes_are_refused_quickly() -> None:
    big = "a=" + "b" * 10_000_000
    for call in (lambda: parse(big), lambda: parse(big, strict=True), lambda: build("a", big[2:])):
        assert _seconds(call) < 2.0
