from __future__ import annotations

import io
import json
from collections.abc import Callable
from typing import Any

import pytest

from setcookie._cli import main

Result = tuple[int, Any, str]


@pytest.fixture
def run(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> Callable[..., Result]:
    def invoke(argv: list[str], stdin: str = "") -> Result:
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
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
