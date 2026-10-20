"""Contracts for the behaviour fixed after the second pass of the five QA lenses."""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest

import setcookie
from setcookie import CookieError, build, parse, parse_date, receive

NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)


def test_the_public_suffix_callable_gets_the_domain_without_a_trailing_dot() -> None:
    seen: list[str] = []

    def suffix(domain: str) -> bool:
        seen.append(domain)
        return domain in {"co.uk", "uk"}

    with pytest.raises(CookieError, match="public suffix"):
        receive("a=1; Domain=co.uk.", "https://x.co.uk./", now=NOW, is_public_suffix=suffix)
    assert seen == ["co.uk"]
    stored = receive("a=1; Domain=CO.UK.", "https://co.uk./", now=NOW, is_public_suffix=suffix)
    assert (stored.domain, stored.host_only) == ("co.uk.", True)


def test_build_refuses_an_extension_name_given_twice() -> None:
    message = r"^extension 'priority' is given twice$"
    with pytest.raises(CookieError, match=message):
        build("a", "b", extensions=[("Priority", "High"), ("priority", "Low")])
    with pytest.raises(CookieError, match=r"^extension 'X' is given twice$"):
        build("a", "b", extensions=[("x", None), ("X", None)])
    with pytest.raises(CookieError, match=r"^extension 'Priority' is given twice$"):
        parse("a=b; Priority=High; Priority=Low").header()


def test_a_bad_cookie_name_names_the_rule_it_breaks() -> None:
    with pytest.raises(CookieError, match=r"^cookie name is empty$"):
        build("", "x")
    with pytest.raises(
        CookieError, match=r"^cookie name 'a b' has U\+0020 at index 1, outside tchar$"
    ):
        build("a b", "x")


def test_the_public_functions_report_the_public_module() -> None:
    for name in ("build", "expire", "parse", "parse_date", "receive"):
        assert getattr(setcookie, name).__module__ == "setcookie", name


@pytest.mark.parametrize(
    "host",
    [
        "a\x00b.com",
        "a\x1bb.com",
        "a\x07",
        "exa mple.com",
        "a<b.com",
        "a>b",
        "a^b.com",
        "a|b.com",
        "a%25b.com",
        "a%00b.com",
        "a\x7fb.com",
        "a%3Ab.com",
        "a%zzb.com",
    ],
)
def test_a_host_with_a_forbidden_code_point_is_refused(host: str) -> None:
    with pytest.raises(CookieError, match="cannot be canonicalized"):
        receive("a=b", f"https://{host}/x", now=NOW)
    stored = receive("a=b", "https://example.com/x", now=NOW)
    with pytest.raises(CookieError, match="cannot be canonicalized"):
        stored.matches(f"https://{host}/x")


def test_the_host_is_percent_decoded_as_a_url_parser_does() -> None:
    assert receive("a=b", "https://ex%41mple.com/", now=NOW).domain == "example.com"
    assert receive("a=b", "https://a%2eb.com/", now=NOW).domain == "a.b.com"
    assert receive("a=b", "https://a_b.com/", now=NOW).domain == "a_b.com"


def test_a_huge_hostile_host_fails_fast() -> None:
    hosts = [
        "".join(chr(0x4E00 + i) for i in range(32000)) + ".com",
        "é." * 32000,
        "a" * 64 + ".com",
        "a." * 126 + "com",
    ]
    for host in hosts:
        started = time.perf_counter()
        with pytest.raises(CookieError, match="cannot be canonicalized"):
            receive("a=b", f"https://{host}/", now=NOW)
        assert time.perf_counter() - started < 0.05
    assert receive("a=b", "https://" + "a." * 125 + "com./", now=NOW).domain.endswith("com.")
    assert receive("a=b", "https://" + "a" * 63 + ".com/", now=NOW).host_only


@pytest.mark.parametrize(
    ("path", "stored"),
    [
        ("/a/../b/c", "/b"),
        ("/a b/c", "/a%20b"),
        ("/é/x", "/%C3%A9"),
        ("/a/./b/c", "/a/b"),
        ("/a/%2e%2E/b/c", "/b"),
        ("/a/..", "/"),
        ('/"<>^`{}/x', "/%22%3C%3E%5E%60%7B%7D"),
        ("/%41/x", "/%41"),
    ],
)
def test_the_request_path_is_normalised_as_a_url_parser_does(path: str, stored: str) -> None:
    assert receive("a=b", f"https://www.example.com{path}", now=NOW).path == stored


def test_matches_normalises_the_request_path() -> None:
    stored = receive("a=b; Path=/b", "https://example.com/", now=NOW)
    assert stored.matches("https://example.com/a/../b")
    assert not stored.matches("https://example.com/b/../a")
    spaced = receive("a=b; Path=/a%20b", "https://example.com/", now=NOW)
    assert spaced.matches("https://example.com/a b/c")


def test_strict_accepts_a_leap_second_and_names_an_impossible_date() -> None:
    cookie = parse("a=b; Expires=Tue, 30 Jun 2015 23:59:60 GMT", strict=True)
    assert cookie.expires is None  # section 5.1.1 refuses second 60, so user agents drop it
    for text in (
        "Sun, 31 Feb 2030 00:00:00 GMT",
        "Sat, 01 Jan 0000 00:00:00 GMT",
        "Tue, 30 Jun 2015 24:00:00 GMT",
        "Tue, 30 Jun 2015 23:58:60 GMT",
    ):
        with pytest.raises(CookieError, match=r"is an IMF-fixdate of a moment that does not"):
            parse(f"a=b; Expires={text}", strict=True)
    with pytest.raises(CookieError, match=r"is not an IMF-fixdate$"):
        parse("a=b; Expires=Tue, 30 Jun 2015 23:59 GMT", strict=True)


class _Hide(str):
    def __iter__(self) -> Iterator[str]:
        return iter("")

    def partition(self, sep: str) -> tuple[str, str, str]:
        return ("a=b", "", "")


def test_a_str_subclass_is_read_as_the_text_it_holds() -> None:
    with pytest.raises(CookieError, match="control character"):
        parse(_Hide("a=b\r\nX-Evil: 1"))
    with pytest.raises(CookieError, match="control character"):
        receive(_Hide("a=b\r\nX: 1"), "https://h.example/", now=NOW)
    with pytest.raises(CookieError, match="cannot be canonicalized"):
        receive("a=b", _Hide("https://a\x00b.com/"), now=NOW)
    assert parse_date(_Hide("Wed, 09 Jun 2021 10:18:14 GMT")) == datetime(
        2021, 6, 9, 10, 18, 14, tzinfo=timezone.utc
    )


def test_max_age_zero_is_expired_even_at_the_earliest_aware_time() -> None:
    stored = receive("a=1; Max-Age=0", "https://x.com/", now=NOW)
    earliest = datetime.min.replace(tzinfo=timezone(timedelta(hours=14)))
    assert stored.is_expired(earliest)
    assert stored.is_expired(NOW)
