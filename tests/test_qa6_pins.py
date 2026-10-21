"""Promises the second pass of the QA lenses showed were not pinned, and the CLI pipe."""

from __future__ import annotations

import io
import json
import os
import string
import subprocess
import sys
from datetime import datetime, timedelta, timezone, tzinfo

import pytest

import setcookie
from setcookie import CookieError, build, parse, receive
from setcookie._cli import main

NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)
# RFC 9110 section 5.6.2: tchar is these 15 symbols, DIGIT and ALPHA.
TCHAR = set("!#$%&'*+-.^_`|~" + string.digits + string.ascii_letters)


class _Bytes:
    """A stdin that hands its bytes over through ``buffer``, as a real stdin does."""

    def __init__(self, data: bytes) -> None:
        self.buffer = io.BytesIO(data)


class _NoOffset(tzinfo):
    def utcoffset(self, moment: datetime | None) -> timedelta | None:
        return None

    def dst(self, moment: datetime | None) -> timedelta | None:
        return None

    def tzname(self, moment: datetime | None) -> str | None:
        return None


def test_a_host_prefix_survives_a_public_suffix_domain_reset_to_host_only() -> None:
    line = "__Host-a=1; Secure; Path=/; Domain=github.io"
    stored = receive(
        line, "https://github.io/", now=NOW, is_public_suffix=lambda d: d == "github.io"
    )
    assert (stored.domain, stored.host_only, stored.name) == ("github.io", True, "__Host-a")


@pytest.mark.parametrize("space", ["\u00a0", "\u0085", "\u3000"])
def test_strict_refuses_non_ascii_whitespace_at_the_edges_of_an_extension(space: str) -> None:
    for av in (f"ext{space}", f"{space}ext"):
        with pytest.raises(CookieError, match="outside av-octet"):
            parse(f"a=b; {av}", strict=True)
        assert parse(f"a=b; {av}").extensions == ((av, None),)


@pytest.mark.parametrize("code", range(128))
def test_a_cookie_name_is_exactly_an_http_token(code: int) -> None:
    char = chr(code)
    if char in TCHAR:
        assert build(f"a{char}", "1") == f"a{char}=1; Path=/"
        assert parse(f"a{char}=1", strict=True).name == f"a{char}"
        return
    with pytest.raises(CookieError, match=f"U\\+{code:04X} at index 1, outside tchar"):
        build(f"a{char}", "1")
    if char not in "=;\t ":
        with pytest.raises(CookieError):
            parse(f"a{char}=1", strict=True)


def test_receive_refuses_a_now_whose_tzinfo_gives_no_offset() -> None:
    with pytest.raises(ValueError, match=r"^now must be an aware datetime$"):
        receive("a=1", "https://example.com/", now=datetime(2026, 10, 21, tzinfo=_NoOffset()))


def test_is_expired_refuses_a_now_whose_tzinfo_gives_no_offset() -> None:
    stored = receive("a=1; Max-Age=60", "https://example.com/", now=NOW)
    with pytest.raises(ValueError, match=r"^now must be an aware datetime$"):
        stored.is_expired(datetime(2026, 10, 22, tzinfo=_NoOffset()))


@pytest.mark.parametrize("extensions", ["", "Priority=High", b""])
def test_extensions_given_as_a_string_raise_type_error(extensions: object) -> None:
    with pytest.raises(TypeError, match=r"^extensions must be an iterable of"):
        build("a", "1", extensions=extensions)  # type: ignore[arg-type]


def test_a_header_dump_field_may_have_space_before_its_colon(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    dump = b"HTTP/1.1 200 OK\r\nSet-Cookie : a=1\r\nSet-Cookie\t:b=2\r\n"
    monkeypatch.setattr("sys.stdin", _Bytes(dump))
    assert main([]) == 0
    report = json.loads(capsys.readouterr().out)
    assert [entry["cookie"]["name"] for entry in report] == ["a", "b"]


def test_a_long_quoted_text_is_cut_and_its_length_given() -> None:
    expected = repr("a" * 40) + r"... \(51 characters\) has U\+0040 at index 50, outside tchar$"
    with pytest.raises(CookieError, match=f"^cookie name {expected}"):
        build("a" * 50 + "@", "1")


def test_a_closed_output_pipe_stops_quietly() -> None:
    env = {**os.environ, "PYTHONPATH": os.path.dirname(os.path.dirname(setcookie.__file__))}
    with subprocess.Popen(
        [sys.executable, "-m", "setcookie"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    ) as child:
        assert child.stdin and child.stdout and child.stderr
        child.stdout.close()
        child.stdin.write(b"a=1\n" * 5000)
        child.stdin.close()
        err = child.stderr.read().decode("utf-8", "replace")
        code = child.wait(timeout=120)
    assert "Traceback" not in err and "Exception ignored" not in err, err
    assert code == 141
