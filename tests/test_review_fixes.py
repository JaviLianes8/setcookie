"""Regression tests for the findings of the independent review of this round."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from setcookie import CookieError, build, parse, receive
from setcookie._cli import _lines, _moment

NOW = datetime(2026, 10, 13, tzinfo=timezone.utc)


def test_a_header_dump_without_set_cookie_yields_no_lines() -> None:
    assert _lines([], "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n") == []
    assert _lines([], "HTTP/2 204\r\nset-cookie: a=1\r\n") == ["a=1"]
    assert _lines([], "a=1\nb=2\n") == ["a=1", "b=2"]


def test_a_path_with_outer_whitespace_is_refused() -> None:
    for path in ("/a ", "/a\t", "/a/ "):
        with pytest.raises(CookieError, match="whitespace"):
            build("a", "b", path=path, secure=True)


def test_a_malformed_url_raises_cookie_error() -> None:
    with pytest.raises(CookieError, match="malformed"):
        receive("a=b", "https://[::1/", now=NOW)


def test_a_fake_a_label_host_is_refused() -> None:
    with pytest.raises(CookieError, match="canonicalized"):
        receive("a=b", "https://xn--zz.de/", now=NOW)
    assert receive("a=b", "https://xn--bcher-kva.example/", now=NOW).host_only


@pytest.mark.parametrize(
    "options",
    [
        {"domain": 5},
        {"path": 5},
        {"extensions": [(1, "x")]},
        {"extensions": [("X", 1)]},
        {"extensions": ["ab"]},
        {"extensions": [("a", "b", "c")]},
        {"max_age": 10**5000},
        {"max_age": 10**1024},
        {"expires": datetime(9999, 12, 31, 23, tzinfo=timezone(timedelta(hours=-5)))},
        {"expires": datetime.min.replace(tzinfo=timezone(timedelta(hours=5)))},
    ],
)
def test_bad_build_arguments_raise_cookie_error(options: dict[str, object]) -> None:
    with pytest.raises(CookieError):
        build("a", "b", **options)  # type: ignore[arg-type]


def test_the_largest_max_age_that_fits_an_attribute_is_written() -> None:
    header = build("a", "b", max_age=10**1024 - 1, path=None)
    assert parse(header, strict=True).max_age == 10**1024 - 1


def test_now_accepts_a_trailing_z() -> None:
    assert _moment("2026-10-13T00:00:00Z") == NOW
    assert _moment("2026-10-13T00:00:00") == NOW


def test_a_repeated_attribute_resets_as_the_model_docstring_says() -> None:
    assert parse("a=b; SameSite=Strict; SameSite=bogus").same_site is None
    assert parse("a=b; Domain=x.com; Domain=").domain is None
    assert parse("a=b; Max-Age=5; Max-Age=x").max_age == 5
