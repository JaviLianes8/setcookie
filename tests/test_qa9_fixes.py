"""Contracts for the behaviour fixed after the fourth QA round of the second full pass."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from setcookie import CookieError, receive
from setcookie._url import request_of

NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)
BS = "\\"

# Expected hosts and paths measured with Node.js 24.18.0 `new URL(...)` (WHATWG URL parser);
# a stored cookie path is the directory of the URL path (section 5.1.4).


@pytest.mark.parametrize(
    ("url", "host"),
    [
        ("http://[::1]@a.com/p/q", "a.com"),
        ("http://[::1]:x@a.com/p/q", "a.com"),
        ("https://u[x]@a.com/p/q", "a.com"),
        ("http://a]@b.com/p/q", "b.com"),
        ("http://[@[::1]/p/q", "::1"),
    ],
)
def test_brackets_in_the_userinfo_do_not_hide_the_host(url: str, host: str) -> None:
    assert request_of(url)[:2] == (host, "/p/q")
    stored = receive("a=1", url, now=NOW)
    assert (stored.domain, stored.path) == (host, "/p")
    assert stored.matches(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://u:pw@x.com/a/b",
        "https://u:1@x.com/a/b",
        "https://u:@x.com/a/b",
        "https://a@b:x@x.com/a/b",
        "https://a:b@c:d@x.com/a/b",
        "https://u@x.com:443/a/b",
    ],
)
def test_a_colon_in_the_userinfo_is_not_a_port(url: str) -> None:
    stored = receive("a=1", url, now=NOW)
    assert (stored.domain, stored.path) == ("x.com", "/a")


@pytest.mark.parametrize(
    ("url", "host", "path"),
    [
        ("http://a@b@c.com/x/y?y@z#q@w", "c.com", "/x/y"),
        ("https://x.com/a@b/c", "x.com", "/a@b/c"),
        ("https://x.com/a//u@b/c", "x.com", "/a//u@b/c"),
        ("https://u@x.com?q@a", "x.com", ""),
        ("https://u@[::1]:8/a/b", "::1", "/a/b"),
        (f"https://x.com{BS}u@evil.com/a", "x.com", "/u@evil.com/a"),
    ],
)
def test_only_the_authority_loses_its_userinfo(url: str, host: str, path: str) -> None:
    assert request_of(url)[:2] == (host, path)


@pytest.mark.parametrize(
    "url",
    [
        "http://[::1]:99999/",
        "http://[::1]:a/",
        "http://[::1]:65536/a",
        "http://[::1]:]/",
        "http://[::1]:8]/",
        "http://u@[::1]:99999/",
        "http://[::1]@x.com:99999/",
    ],
)
def test_a_bad_port_after_a_bracketed_host_is_malformed(url: str) -> None:
    with pytest.raises(CookieError, match="the request URL is malformed"):
        receive("a=1", url, now=NOW)


@pytest.mark.parametrize(
    "url",
    [f"http//x.com{BS}a/b", "https//x.com/a/b", "wss x.com/a/b", "http;//x.com/a/b"],
)
def test_a_special_scheme_needs_its_colon(url: str) -> None:
    with pytest.raises(CookieError, match="the request URL has no host"):
        receive("a=1", url, now=NOW)


def test_a_scheme_is_only_read_at_the_start_of_the_url() -> None:
    assert request_of(f"//x.com/http:{BS}a")[:2] == ("x.com", f"/http:{BS}a")
    stored = receive("a=1", f"//x.com/http:{BS}a", now=NOW)
    assert (stored.domain, stored.path) == ("x.com", "/")
