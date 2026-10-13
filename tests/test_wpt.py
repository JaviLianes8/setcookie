"""Run the web-platform-tests cookie parser cases through `receive` and a small jar.

The pages are read from tests/upstream/wpt (URL, commit and sha256 in MANIFEST.json); the
tests skip until `python scripts/fetch_upstream.py` has fetched them. The harness of
cookies/resources/cookie-test.js sets each line from SET_URL and reads document.cookie at
the page, or at echo-cookie.html for cases that use the default path.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from conftest import read_upstream
from wpt_cases import Case, cases, name_loop

from setcookie import CookieError, StoredCookie, receive

HOST = "http://web-platform.test"
SET_URL = f"{HOST}/cookies/resources/cookie.py"
DEFAULT_PATH_PAGE = f"{HOST}/cookies/resources/echo-cookie.html"
NOW = datetime(2026, 10, 13, tzinfo=timezone.utc)
PAGES = {
    "wpt/name.html": "/cookies/name/name.html",
    "wpt/value.html": "/cookies/value/value.html",
    "wpt/max-age.html": "/cookies/attributes/max-age.html",
    "wpt/invalid.html": "/cookies/attributes/invalid.html",
    "wpt/expires.html": "/cookies/attributes/expires.html",
    "wpt/path.html": "/cookies/attributes/path.html",
    "wpt/size-name-and-value.html": "/cookies/size/name-and-value.html",
}
# Expected counts per page, so a reader that silently drops cases fails.
COUNTS = {
    "wpt/name.html": 27,
    "wpt/value.html": 28,
    "wpt/max-age.html": 10,
    "wpt/invalid.html": 26,
    "wpt/expires.html": 11,
    "wpt/path.html": 21,
    "wpt/size-name-and-value.html": 11,
}


def _transport_safe(line: str) -> bool:
    # CR, LF and NUL end or break the header field on the wire (RFC 9110 section 5.5), so
    # what reaches the parser depends on the server, not on cookie parsing.
    return not any(char in line for char in "\r\n\0")


def _cookie_string(case: Case, page: str) -> str:
    jar: dict[tuple[str, str, bool, str], tuple[int, StoredCookie]] = {}
    for order, line in enumerate(case.cookie):
        try:
            cookie = receive(line, SET_URL, now=NOW)
        except CookieError:
            continue
        key = (cookie.name, cookie.domain, cookie.host_only, cookie.path)
        created = jar[key][0] if key in jar else order
        jar[key] = (created, cookie)
        jar = {k: v for k, v in jar.items() if not v[1].is_expired(NOW)}
    url = DEFAULT_PATH_PAGE if case.default_path else HOST + page
    visible = [(c, cookie) for c, cookie in jar.values() if cookie.matches(url)]
    visible.sort(key=lambda item: (-len(item[1].path), item[0]))
    return "; ".join(
        f"{cookie.name}={cookie.value}" if cookie.name else cookie.value for _, cookie in visible
    )


@pytest.mark.parametrize("name", sorted(PAGES))
def test_every_web_platform_case_matches(name: str) -> None:
    found = cases(read_upstream(name))
    assert len(found) == COUNTS[name]
    checked = 0
    for case in found:
        if not all(_transport_safe(line) for line in case.cookie):
            continue
        assert _cookie_string(case, PAGES[name]) == case.expected, case.name
        checked += 1
    assert checked >= COUNTS[name] - 1


def test_the_name_loop_of_name_html_sets_each_name() -> None:
    names = name_loop(read_upstream("wpt/name.html"))
    assert len(names) == 18
    for name in names:
        line = f"{name}=test"
        assert _cookie_string(Case((line,), line, line, True), PAGES["wpt/name.html"]) == line
