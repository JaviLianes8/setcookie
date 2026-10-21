"""Contracts for the behaviour pinned after the seventh QA round of the second full pass."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from setcookie import CookieError, receive
from setcookie._url import request_of

NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)

# Node.js 24.18.0 `new URL(...)` (WHATWG URL parser) throws ERR_INVALID_URL for every URL
# below. The first two groups matter on Python 3.10, whose urlsplit may read a scheme
# that starts with a digit, a sign or a dot.


@pytest.mark.parametrize(
    "url",
    [
        "0http://x.com/a",
        "0a://u@x.com/a",
        "0://x.com/a",
        "0.0://1.2.3.4/a",
    ],
)
def test_a_prefix_that_starts_with_zero_has_no_host(url: str) -> None:
    with pytest.raises(CookieError, match="the request URL has no host"):
        request_of(url)
    with pytest.raises(CookieError, match="the request URL has no host"):
        receive("a=1", url, now=NOW)


@pytest.mark.parametrize(
    "url",
    [
        " 1http://x.com/a",
        "\t1http://x.com/a",
        "\t1http://[/a",
        "\x001http://[/a",
        " 1http://[/a",
        " +a://x[/a",
        "\n-a://[/a",
    ],
)
def test_a_prefix_after_stripped_characters_has_no_host(url: str) -> None:
    with pytest.raises(CookieError, match="the request URL has no host"):
        request_of(url)
    with pytest.raises(CookieError, match="the request URL has no host"):
        receive("a=1", url, now=NOW)


@pytest.mark.parametrize(
    "url",
    [
        "http://:99999/a",
        "foo://:99999/a",
        "http://u@:99999/a",
        "https://:abc/a",
    ],
)
def test_an_invalid_port_without_a_host_is_malformed(url: str) -> None:
    # The port is checked before the host, so a bad port wins over an empty host.
    with pytest.raises(CookieError, match="the request URL is malformed"):
        request_of(url)
    with pytest.raises(CookieError, match="the request URL is malformed"):
        receive("a=1", url, now=NOW)
    with pytest.raises(CookieError, match="the request URL is malformed"):
        receive("a=1", "https://x.com/", now=NOW).matches(url)
