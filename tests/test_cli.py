from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from collections.abc import Callable
from typing import Any

import pytest

import setcookie
from setcookie._cli import main

Result = tuple[int, Any, str]


@pytest.fixture
def run(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> Callable[..., Result]:
    def invoke(argv: list[str], stdin: str | bytes = "") -> Result:
        data = stdin.encode() if isinstance(stdin, str) else stdin
        # A cp1252 text layer like a Windows console: the CLI must read the bytes beneath it.
        monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(data), encoding="cp1252"))
        code = main(argv)
        out, err = capsys.readouterr()
        return code, json.loads(out) if out else None, err

    return invoke


def test_parses_lines_given_as_arguments(run: Callable[..., Result]) -> None:
    code, report, err = run(["sid=abc; Path=/; Max-Age=60", "x=1"])
    assert code == 0 and err == ""
    assert isinstance(report, list) and len(report) == 2
    assert report[0]["cookie"]["max_age"] == 60
    assert report[0]["cookie"]["extensions"] == []


def test_reads_only_set_cookie_fields_from_a_header_dump(run: Callable[..., Result]) -> None:
    dump = (
        "HTTP/2 200\r\ncontent-type: text/html\r\nset-cookie: a=1; Secure\r\n"
        "Set-Cookie:b=2\r\nX-Other: c=3\r\n\r\n"
    )
    code, report, _ = run([], dump)
    assert code == 0
    assert isinstance(report, list)
    assert [entry["cookie"]["name"] for entry in report] == ["a", "b"]


def test_plain_stdin_lines_are_each_a_cookie(run: Callable[..., Result]) -> None:
    code, report, _ = run([], "a=1\n\n b=2 \n")
    assert code == 0 and isinstance(report, list)
    assert [entry["cookie"]["value"] for entry in report] == ["1", "2"]


def test_strict_reports_the_rule_and_exits_one(run: Callable[..., Result]) -> None:
    code, report, err = run(["--strict", "sid=a b", "ok=1"])
    assert code == 1
    assert isinstance(report, list)
    assert "cookie-octet" in report[0]["error"] and "cookie" in report[1]
    assert "setcookie: strict:" in err


def test_url_shows_the_stored_cookie(run: Callable[..., Result]) -> None:
    argv = ["--url", "https://www.example.com/a/b", "--now", "2026-10-13T00:00:00"]
    code, report, _ = run([*argv, "sid=a; Max-Age=60; Domain=example.com"])
    assert code == 0 and isinstance(report, list)
    stored = report[0]["stored"]
    assert stored["domain"] == "example.com" and stored["path"] == "/a"
    assert stored["expiry"] == "2026-10-13T00:01:00+00:00"


def test_url_reports_a_rejected_cookie(run: Callable[..., Result]) -> None:
    code, report, err = run(["--url", "http://h.test/", "a=1; Secure"])
    assert code == 1 and isinstance(report, list)
    assert "insecure" in report[0]["error"] and "insecure" in err


def test_no_input_is_a_usage_error(run: Callable[..., Result]) -> None:
    with pytest.raises(SystemExit) as caught:
        run([], "\n\n")
    assert caught.value.code == 2


def test_a_header_dump_without_set_cookie_prints_an_empty_list(
    run: Callable[..., Result],
) -> None:
    for dump in ("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n", "HTTP/2 204\n"):
        code, report, err = run(["--strict"], dump)
        assert (code, report, err) == (0, [], "")


def test_set_cookie_fields_without_a_status_line_are_a_dump(run: Callable[..., Result]) -> None:
    code, report, _ = run([], "a=1\nSet-Cookie: b=2\nset-cookie:c=3\n")
    assert code == 0 and isinstance(report, list)
    assert [entry["line"] for entry in report] == ["b=2", "c=3"]


def test_stdin_is_decoded_as_utf_8_whatever_the_locale(run: Callable[..., Result]) -> None:
    code, report, _ = run([], b"\xef\xbb\xbfsid=caf\xc3\xa9\n")
    assert code == 0 and isinstance(report, list)
    assert report[0]["cookie"]["name"] == "sid"
    assert report[0]["cookie"]["value"] == "café"
    code, report, err = run(["--strict"], b"sid=caf\xc3\xa9\n")
    assert code == 1 and "U+00E9 at index 3" in err


def test_bytes_that_are_not_utf_8_do_not_crash(run: Callable[..., Result]) -> None:
    code, report, _ = run([], b"sid=a\xffb\n")
    assert code == 0 and isinstance(report, list) and report[0]["cookie"]["name"] == "sid"
    assert report[0]["cookie"]["value"] == "a\udcffb"


def _closed_stdin_run(command: list[str], **options: Any) -> None:
    # The child imports the same setcookie as these tests, installed or from src.
    env = {**os.environ, "PYTHONPATH": os.path.dirname(os.path.dirname(setcookie.__file__))}
    done = subprocess.run(command, capture_output=True, text=True, check=False, env=env, **options)
    assert done.returncode == 2, done.stderr
    assert "no Set-Cookie line given" in done.stderr and "Traceback" not in done.stderr


def test_closed_stdin_is_a_usage_error_not_a_crash() -> None:
    # Python sets sys.stdin to None when descriptor 0 is closed (`setcookie <&-`).
    code = "import sys; sys.stdin = None; from setcookie._cli import main; sys.exit(main([]))"
    _closed_stdin_run([sys.executable, "-c", code])
    if sys.platform != "win32":
        _closed_stdin_run([sys.executable, "-m", "setcookie"], preexec_fn=lambda: os.close(0))


def test_now_keeps_its_offset(run: Callable[..., Result]) -> None:
    argv = ["--url", "https://h.example/", "--now", "2026-10-13T00:00:00+02:00", "a=b; Max-Age=60"]
    code, report, _ = run(argv)
    assert code == 0 and isinstance(report, list)
    assert report[0]["stored"]["expiry"] == "2026-10-13T00:01:00+02:00"


def test_a_host_the_codec_cannot_decode_is_reported_not_raised(
    run: Callable[..., Result],
) -> None:
    code, report, err = run(["--url", "https://xn--99999999999999999999a/", "sid=1"])
    assert code == 1 and isinstance(report, list)
    assert "canonicalized" in report[0]["error"] and "canonicalized" in err


def test_stdin_lines_keep_their_outer_whitespace(run: Callable[..., Result]) -> None:
    code, report, err = run(["--strict"], "a=1 \n")
    assert code == 1 and isinstance(report, list)
    assert report[0]["line"] == "a=1 " and "trailing whitespace" in report[0]["error"]
    assert "setcookie: strict:" in err
    code, report, _ = run([], "  a=1\n")
    assert code == 0 and isinstance(report, list)
    assert report[0]["line"] == "  a=1" and report[0]["cookie"]["value"] == "1"


def test_a_text_stdin_without_a_byte_buffer_is_read(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # An embedding host may swap sys.stdin for a plain text stream such as StringIO.
    monkeypatch.setattr("sys.stdin", io.StringIO("a=1\n"))
    assert main([]) == 0
    out, err = capsys.readouterr()
    assert err == ""
    assert [entry["cookie"]["name"] for entry in json.loads(out)] == ["a"]
