"""Contracts for the behaviour pinned after the sixth QA round of the second full pass."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from setcookie import CookieError, receive
from setcookie._url import request_of

NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)

# Node.js 24.18.0 `new URL(...)` (WHATWG URL parser) throws for every refused URL below and
# gives the host `x.com` and the path `/a` for both accepted ones.


@pytest.mark.parametrize(
    "url",
    [
        "1http://[/a",
        "+a://x[/a",
        "9a://[@?q",
        "1http://]/a",
        "-a://u@[x/a",
        ".a://[::1/a",
        "1http://[x]/a",
        "1http://[::1]x/a",
        "-a://x.com/a",
        ".a://u@x.com/a",
        "-://x.com/a",
        ".://x.com/a",
    ],
)
def test_a_prefix_that_is_not_a_scheme_has_no_host(url: str) -> None:
    with pytest.raises(CookieError, match="the request URL has no host"):
        request_of(url)
    with pytest.raises(CookieError, match="the request URL has no host"):
        receive("a=1", url, now=NOW)


@pytest.mark.parametrize("url", ["a://x.com/a", "A://u@x.com/a"])
def test_a_scheme_may_be_one_letter(url: str) -> None:
    assert request_of(url) == ("x.com", "/a", False)
    stored = receive("a=1", url, now=NOW)
    assert stored.domain == "x.com"
    assert stored.matches(url)
