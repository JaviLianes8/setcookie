"""Contracts for the behaviour fixed after the second QA round of the second full pass."""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone

import pytest

from setcookie import CookieError, receive
from setcookie._cli import SIGPIPE_STATUS, main

NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)
BS = "\\"

# Expected hosts and paths measured with Node.js 24.18.0 `new URL(...)` (WHATWG URL parser).


@pytest.mark.parametrize(
    ("url", "domain", "path"),
    [
        (f"https://x.com{BS}@evil.com/p/q", "x.com", "/@evil.com/p"),
        (f"https://exa{BS}mple.com/", "exa", "/mple.com"),
        (f"https://u{BS}p@x.com/a", "u", "/p@x.com"),
        (f"https://x.com/a{BS}b/c", "x.com", "/a/b"),
        (f"https://example.com/a{BS}..{BS}b/c", "example.com", "/b"),
        (f"wss://x.com/a{BS}b/c", "x.com", "/a/b"),
        (f"HTTPS:{BS}{BS}x.com{BS}a{BS}b", "x.com", "/a"),
        ("https:x.com/a/b", "x.com", "/a"),
        ("https:///x.com/a/b", "x.com", "/a"),
        (f"https:/{BS}/x.com/a/b", "x.com", "/a"),
        (f"https://x.com/a/b?q{BS}r/s", "x.com", "/a"),
    ],
)
def test_a_backslash_is_a_slash_in_a_special_url(url: str, domain: str, path: str) -> None:
    stored = receive("a=1", url, now=NOW)
    assert (stored.domain, stored.path) == (domain, path)


def test_a_backslash_is_kept_in_a_url_of_another_scheme() -> None:
    assert receive("a=1", f"foo://x.com/a{BS}b/c", now=NOW).path == f"/a{BS}b"


def test_matches_reads_a_backslash_as_a_slash() -> None:
    stored = receive("a=b; Path=/a/b", "https://example.com/", now=NOW)
    assert stored.matches(f"https://example.com/a{BS}b/c")
    assert receive("a=1", "https://x.com/", now=NOW).matches(f"https://x.com{BS}@evil.com/")
    assert not receive("a=1", "https://evil.com/", now=NOW).matches(f"https://x.com{BS}@evil.com/")


@pytest.mark.parametrize(
    ("host", "domain"),
    [
        ("[0:0::1]", "::1"),
        ("[0000:0000::0001]", "::1"),
        ("[::FFFF:1.2.3.4]", "::ffff:102:304"),
        ("[::1.2.3.4]", "::102:304"),
        ("[1:0:0:2:0:0:0:3]", "1:0:0:2::3"),
        ("[1:0:0:2:0:0:3:4]", "1::2:0:0:3:4"),
        ("[::1:0:0:0:0:0:0]", "0:1::"),
        ("[::]", "::"),
        ("[2001:DB8::]", "2001:db8::"),
        ("[1:2:3:4:5:6:7:8]", "1:2:3:4:5:6:7:8"),
    ],
)
def test_an_ipv6_host_is_serialized_as_a_url_parser_does(host: str, domain: str) -> None:
    assert receive("a=1", f"http://{host}/x", now=NOW).domain == domain


def test_spellings_of_one_ipv6_address_match_each_other() -> None:
    assert receive("a=1", "https://[::1]/", now=NOW).matches("https://[0:0::1]/")
    assert receive("a=1", "https://[0:0::1]/", now=NOW).matches("https://[::1]/")


@pytest.mark.parametrize(
    "host", ["[fe80::1%25eth0]", "[fe80::1%eth0]", "[fe80::1%\x00x]", "[fe80::1%a b<>]"]
)
def test_an_ipv6_zone_id_is_refused(host: str) -> None:
    with pytest.raises(CookieError, match="cannot be canonicalized"):
        receive("a=1", f"https://{host}/", now=NOW)
    stored = receive("a=1", "https://[fe80::1]/", now=NOW)
    with pytest.raises(CookieError, match="cannot be canonicalized"):
        stored.matches(f"https://{host}/")


def test_a_huge_ipv6_zone_id_is_refused() -> None:
    with pytest.raises(CookieError, match="cannot be canonicalized"):
        receive("a=1", "https://[fe80::1%" + "x" * 10**6 + "]/", now=NOW)


def test_a_closed_stderr_leaves_the_json_on_stdout_intact(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.stderr", None)
    code = main(["--strict", "a=1; Expires=x", "b=2"])
    monkeypatch.undo()
    out, _ = capsys.readouterr()
    assert code == 1
    assert [entry["line"] for entry in json.loads(out)] == ["a=1; Expires=x", "b=2"]


def test_a_closed_stdout_stops_without_a_traceback(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.stdout", None)
    code = main(["a=1"])
    monkeypatch.undo()
    assert code == SIGPIPE_STATUS
    assert capsys.readouterr().err == ""


def test_a_closed_stdout_still_reports_failures_on_stderr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    err = io.StringIO()
    monkeypatch.setattr("sys.stdout", None)
    monkeypatch.setattr("sys.stderr", err)
    assert main(["--strict", "a=1; Expires=x"]) == SIGPIPE_STATUS
    assert err.getvalue().startswith("setcookie: ")
