"""build and parse are inverse on normalised values (lower-case domain, aware UTC dates)."""

from __future__ import annotations

import itertools
from datetime import datetime, timezone

import pytest

from setcookie import Cookie, CookieError, build, parse

NAMES = ["sid", "__Secure-sid", "__Host-sid", "a.b_c-d~e"]
VALUES = ["", "abc", '"quoted"', "x=y:z/w?!#"]
EXPIRES = [None, datetime(2030, 12, 31, 23, 59, 59, tzinfo=timezone.utc)]
DOMAINS = [None, "example.com"]
PATHS = [None, "/", "", "/app/x"]
SAME_SITE = [None, "Lax", "Strict", "None"]


def _cases() -> list[Cookie]:
    found = []
    for name, value, expires, domain, path, same_site, flags in itertools.product(
        NAMES, VALUES, EXPIRES, DOMAINS, PATHS, SAME_SITE, range(16)
    ):
        found.append(
            Cookie(
                name=name,
                value=value,
                expires=expires,
                max_age=None if flags & 1 else 3600,
                domain=domain,
                path=path,
                secure=bool(flags & 2),
                http_only=bool(flags & 4),
                same_site=same_site,  # type: ignore[arg-type]
                partitioned=bool(flags & 8),
                extensions=(("Priority", "High"), ("x-flag", None)) if flags & 1 else (),
            )
        )
    return found


def test_every_buildable_cookie_parses_back_strictly() -> None:
    built = refused = 0
    for cookie in _cases():
        try:
            header = cookie.header()
        except CookieError:
            refused += 1
            continue
        assert parse(header, strict=True) == cookie, header
        built += 1
    assert built > 2000 and refused > 1000


def test_refusals_are_exactly_the_prefix_and_secure_rules() -> None:
    for cookie in _cases():
        name = cookie.name.lower()
        expected_ok = (
            cookie.secure or (cookie.same_site != "None" and not cookie.partitioned)
        ) and (not name.startswith(("__secure-", "__host-")) or cookie.secure)
        if name.startswith("__host-"):
            expected_ok = expected_ok and cookie.domain is None and cookie.path == "/"
        try:
            cookie.header()
        except CookieError:
            assert not expected_ok, cookie
        else:
            assert expected_ok, cookie


@pytest.mark.parametrize(
    "line",
    [
        "sid=abc; Path=/; Secure; HttpOnly; SameSite=Lax",
        "sid=abc; Expires=Fri, 02 Jan 2026 03:04:05 GMT; Max-Age=60; Domain=example.com",
        "__Host-id=1; Secure; Path=/; Partitioned; Priority=High",
    ],
)
def test_parse_then_header_is_stable(line: str) -> None:
    once = parse(line).header()
    assert parse(once).header() == once
    assert parse(once) == parse(line)


def test_build_output_never_contains_a_line_break_or_extra_pair() -> None:
    for value in ["a\r\nSet-Cookie: x=y", "a;b=c", "a\nb", "a\x00b"]:
        with pytest.raises(CookieError):
            build("sid", value)
    header = build("sid", "abc", extensions=[("Note", "a=b c")])
    assert parse(header).extensions == (("Note", "a=b c"),)
