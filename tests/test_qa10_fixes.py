"""Contracts for the behaviour pinned after the fifth QA round of the second full pass."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from setcookie import CookieError, receive
from setcookie._url import request_of

NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)
BS = "\\"

# Expected hosts and paths measured with Node.js 24.18.0 `new URL(...)` (WHATWG URL parser).


@pytest.mark.parametrize(
    ("url", "host", "path", "secure"),
    [
        ("HTTPS://u:1@x.com/a/b", "x.com", "/a/b", True),
        ("HTTP://[::1]@a.com/p", "a.com", "/p", False),
        ("web+cal://u:1@x.com/a", "x.com", "/a", False),
        ("foo1://u:1@x.com/a", "x.com", "/a", False),
        ("a.b-c://u:1@x.com/a", "x.com", "/a", False),
        ("https://@[::1]/a/b", "::1", "/a/b", True),
        ("https://@x.com/a/b", "x.com", "/a/b", True),
        (f"foo://a:{BS}b@x.com/a", "x.com", "/a", False),
        (f"foo://a{BS}b:1@[::1]/a", "::1", "/a", False),
    ],
)
def test_the_userinfo_is_dropped_after_any_scheme(
    url: str, host: str, path: str, secure: bool
) -> None:
    assert request_of(url) == (host, path, secure)
    stored = receive("a=1", url, now=NOW)
    assert stored.domain == host
    assert stored.matches(url)


@pytest.mark.parametrize(
    "url",
    [
        "foo:/@/x.com/p",
        "/@/x.com/p",
        "a:/u@/x.com/p",
        "1http://u@x.com/a",
        "+a://u@x.com/a",
        "+a://x.com/a",
        "1http://u:1@x.com/a",
        "9://x.com/a",
    ],
)
def test_a_url_without_an_authority_has_no_host(url: str) -> None:
    with pytest.raises(CookieError, match="the request URL has no host"):
        request_of(url)
    with pytest.raises(CookieError, match="the request URL has no host"):
        receive("a=1", url, now=NOW)


def test_a_bracket_inside_the_host_is_malformed() -> None:
    with pytest.raises(CookieError, match="the request URL is malformed"):
        request_of("http://x[::1]/")
