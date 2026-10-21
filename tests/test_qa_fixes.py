"""Contracts for the behaviour fixed after the independent QA lenses of 1.0.0."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from enum import Enum
from typing import cast

import pytest

from setcookie import CookieError, SameSite, build, expire, parse, receive

NOW = datetime(2026, 10, 20, tzinfo=timezone.utc)
HUGE_LABEL = "xn--99999999999999999999a"


def test_a_trailing_dot_keeps_the_request_host_distinct() -> None:
    stored = receive("a=1", "https://www.example.com./", now=NOW)
    assert stored.domain == "www.example.com." and stored.host_only
    plain = receive("a=1", "https://www.example.com/", now=NOW)
    assert not plain.matches("https://www.example.com./")
    assert not stored.matches("https://www.example.com/")
    assert stored.matches("https://www.example.com./x")
    wide = receive("a=1; Domain=example.com", "https://www.example.com/", now=NOW)
    assert not wide.matches("https://www.example.com./")


def test_a_trailing_dot_host_domain_matches_only_a_dotted_domain() -> None:
    with pytest.raises(CookieError, match="domain-match"):
        receive("a=1; Domain=example.com", "https://www.example.com./", now=NOW)
    stored = receive("a=1; Domain=example.com.", "https://www.example.com./", now=NOW)
    assert stored.domain == "example.com." and not stored.host_only
    assert stored.matches("https://a.b.example.com./")


def test_a_host_of_only_a_dot_cannot_be_canonicalized() -> None:
    with pytest.raises(CookieError, match="canonicalized"):
        receive("a=1", "http://./", now=NOW)


@pytest.mark.parametrize(
    "host",
    [
        "127.1",
        "0x7f.0.0.1",
        "0x7F.1",
        "2130706433",
        "0177.0.0.1",
        "127.0.0.1.",
        "127.0.1",
        "127.0.0.0x1",
    ],
)
def test_ipv4_shorthand_hosts_are_read_as_the_address(host: str) -> None:
    stored = receive("a=1", f"http://{host}/x/y", now=NOW)
    assert stored.domain == "127.0.0.1" and stored.host_only and stored.path == "/x"
    assert stored.matches("http://127.0.0.1/x")
    assert receive("a=1", "http://127.0.0.1/", now=NOW).matches(f"http://{host}/")
    with pytest.raises(CookieError, match="domain-match"):
        receive("a=1; Domain=1", f"http://{host}/", now=NOW)


@pytest.mark.parametrize(
    "host",
    [
        "1.2.3.4.5",
        "256.0.0.1",
        "1.2.3.256",
        "1.16777216",
        "a.09",
        "1.256.0.1",
        "1.2.256.3",
        "1.2.3.4.0",
        "a.1",
        "x.y.127",
        "x.0x1",
        "1.09",
        "09",
    ],
)
def test_a_host_that_ends_in_a_bad_number_is_refused(host: str) -> None:
    with pytest.raises(CookieError, match="canonicalized"):
        receive("a=1", f"http://{host}/", now=NOW)


@pytest.mark.parametrize("host", ["0x", "0x.0x.0x.0x"])
def test_a_bare_hex_prefix_is_the_number_zero(host: str) -> None:
    assert receive("a=1", f"http://{host}/", now=NOW).domain == "0.0.0.0"


def test_names_with_digits_that_are_not_numbers_stay_host_names() -> None:
    assert receive("a=1", "http://a1.example/", now=NOW).domain == "a1.example"
    assert receive("a=1", "http://1.example/", now=NOW).domain == "1.example"
    assert receive("a=1", "http://x.0xg/", now=NOW).domain == "x.0xg"
    assert receive("a=1", "http://x.1a/", now=NOW).domain == "x.1a"
    assert receive("a=1", "http://example.1e/", now=NOW).domain == "example.1e"
    # The WHATWG IPv6 serializer writes the mapped IPv4 part in hexadecimal pieces.
    assert receive("a=1", "http://[::ffff:1.2.3.4]/", now=NOW).domain == "::ffff:102:304"


def test_a_punycode_label_too_large_to_decode_raises_cookie_error() -> None:
    url = f"https://{HUGE_LABEL}/"
    with pytest.raises(CookieError, match="canonicalized"):
        receive("sid=1", url, now=NOW)
    stored = receive("sid=1", "https://example.com/", now=NOW)
    with pytest.raises(CookieError, match="canonicalized"):
        stored.matches(url)


class _Names(str, Enum):
    SESSION = "sid"


class _Paths(str, Enum):
    ROOT = "/"


class _Sites(str, Enum):
    LAX = "Lax"


class _LyingStr(str):
    def __format__(self, spec: str) -> str:
        return "a=b; Domain=evil.example; x"


class _LyingInt(int):
    def __format__(self, spec: str) -> str:
        return "1; Domain=evil.example"


def test_build_writes_the_value_an_enum_member_holds() -> None:
    # The SameSite literal type refuses the member; the runtime accepts what it holds.
    lax: SameSite = cast("SameSite", _Sites.LAX)
    line = build(_Names.SESSION, "abc", path=_Paths.ROOT, same_site=lax)
    assert line == "sid=abc; Path=/; SameSite=Lax"
    assert expire(_Names.SESSION, path=_Paths.ROOT) == (
        "sid=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/"
    )
    assert build("a", "b", extensions=[(_Names.SESSION, _Paths.ROOT)]) == "a=b; Path=/; sid=/"


def test_a_subclass_with_its_own_format_cannot_inject_attributes() -> None:
    assert build(_LyingStr("sid"), "abc") == "sid=abc; Path=/"
    assert build("sid", _LyingStr("abc"), domain=_LyingStr("h.example")) == (
        "sid=abc; Domain=h.example; Path=/"
    )
    assert build("sid", "abc", max_age=_LyingInt(5)) == "sid=abc; Max-Age=5; Path=/"
    assert build("a", "b", extensions=[(_LyingStr("k"), _LyingStr("v"))]) == "a=b; Path=/; k=v"
    for line in (build(_LyingStr("sid"), "abc"), build("s", "a", max_age=_LyingInt(5))):
        assert parse(line, strict=True).domain is None


class _Floating(tzinfo):
    def utcoffset(self, moment: datetime | None) -> timedelta | None:
        return None

    def dst(self, moment: datetime | None) -> timedelta | None:
        return None

    def tzname(self, moment: datetime | None) -> str | None:
        return None


def test_build_takes_a_floating_tzinfo_as_utc_like_a_naive_datetime() -> None:
    floating = datetime(2030, 1, 1, 12, tzinfo=_Floating())
    expected = "sid=abc; Expires=Tue, 01 Jan 2030 12:00:00 GMT; Path=/"
    assert build("sid", "abc", expires=floating) == expected
    assert build("sid", "abc", expires=datetime(2030, 1, 1, 12)) == expected
