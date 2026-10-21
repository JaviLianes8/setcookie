"""Contracts for the behaviour fixed after the third QA round of the second full pass."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from setcookie import CookieError, receive
from setcookie._cli import main
from setcookie._url import request_of

NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)
BS = "\\"

# Expected hosts and paths measured with Node.js 24.18.0 `new URL(...)` (WHATWG URL parser);
# a stored cookie path is the directory of the URL path (section 5.1.4), and `request_of`
# keeps an empty URL path empty, which that step reads as "/".


@pytest.mark.parametrize(
    "url",
    [
        f"https://u:p{BS}@x.com/a/b",
        f"https://evil.com:x{BS}@bank.com/a",
        "https://x.com:abc/a/b",
        "https://x.com:99999/a/b",
        "https://x.com:65536/a",
        "https://x.com:+1/a",
        "https://x.com:\u0661/a",
        "http://[::1]:abc/",
        "http://[::1]x/",
    ],
)
def test_a_url_with_an_invalid_port_is_malformed(url: str) -> None:
    with pytest.raises(CookieError, match="the request URL is malformed"):
        receive("a=1", url, now=NOW)
    with pytest.raises(CookieError, match="the request URL is malformed"):
        receive("a=1", "https://x.com/", now=NOW).matches(url)


@pytest.mark.parametrize(
    ("url", "domain", "path"),
    [
        ("https://x.com:/a/b", "x.com", "/a"),
        ("https://x.com:0/a/b", "x.com", "/a"),
        ("https://x.com:65535/a/b", "x.com", "/a"),
        (f"https://[::1]:8/a{BS}b/c", "::1", "/a/b"),
    ],
)
def test_a_valid_or_empty_port_is_accepted(url: str, domain: str, path: str) -> None:
    stored = receive("a=1", url, now=NOW)
    assert (stored.domain, stored.path) == (domain, path)


@pytest.mark.parametrize(
    ("url", "host", "path"),
    [
        ("https://x.com/a/b ", "x.com", "/a/b"),
        ("https://x.com/a/b  ", "x.com", "/a/b"),
        ("https://x.com/a/b\x01", "x.com", "/a/b"),
        ("https://x.com/a/b\t ", "x.com", "/a/b"),
        ("https://x.com ", "x.com", ""),
        ("http://a.com\x1f", "a.com", ""),
        ("  http://a.com/\x1f", "a.com", "/"),
        (f" https://x.com{BS}a/b", "x.com", "/a/b"),
        (f"\x01https://x.com{BS}a/b", "x.com", "/a/b"),
        ("\x00 \x1fhttps://x.com/a/b \x00", "x.com", "/a/b"),
    ],
)
def test_c0_controls_and_spaces_are_stripped_at_both_ends(url: str, host: str, path: str) -> None:
    assert request_of(url)[:2] == (host, path)
    assert receive("a=1", url, now=NOW).domain == host


def test_matches_strips_a_trailing_space_of_the_url() -> None:
    stored = receive("a=b; Path=/a/b", "https://x.com/", now=NOW)
    assert stored.matches("https://x.com/a/b ")
    assert stored.matches("https://x.com/a/b\x01")


@pytest.mark.parametrize("removed", ["\t", "\n", "\r"])
def test_tab_and_newlines_are_removed_from_the_scheme(removed: str) -> None:
    stored = receive("a=1", f"ht{removed}tps://x.com{BS}a/b", now=NOW)
    assert (stored.domain, stored.path) == ("x.com", "/a")


@pytest.mark.parametrize(
    ("url", "domain", "path"),
    [
        (f"http://[::1]{BS}x/y", "::1", "/x"),
        (f"http://[::1]{BS}", "::1", "/"),
        (f"HTTP://[::1]{BS}x/y", "::1", "/x"),
        (f"wss://[2001:db8::1]{BS}a{BS}b", "2001:db8::1", "/a"),
    ],
)
def test_a_backslash_may_follow_a_bracketed_host(url: str, domain: str, path: str) -> None:
    stored = receive("a=1", url, now=NOW)
    assert (stored.domain, stored.path) == (domain, path)


@pytest.mark.parametrize("scheme", ["ftp", "http", "https", "ws", "wss"])
def test_every_special_scheme_reads_a_backslash_as_a_slash(scheme: str) -> None:
    stored = receive("a=1", f"{scheme}://x.com{BS}a/b", now=NOW)
    assert (stored.domain, stored.path) == ("x.com", "/a")
    stored = receive("a=1", f"{scheme}://x.com{BS}@evil.com/p/q", now=NOW)
    assert (stored.domain, stored.path) == ("x.com", "/@evil.com/p")


def test_every_failing_line_gets_its_own_stderr_line(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--strict", "a=1; Expires=x", "b=2; Max-Age=y"]) == 1
    assert capsys.readouterr().err == (
        "setcookie: strict: Expires='x' is not an IMF-fixdate\n"
        "setcookie: strict: Max-Age='y' is not a non-zero-digit followed by DIGITs\n"
    )
