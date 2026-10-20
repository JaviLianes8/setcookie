"""The command reads stdin only when no Set-Cookie line is given on the command line."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from setcookie._cli import main


class _OpenStdin:
    """A stdin that never reaches EOF, such as a terminal: reading it would block."""

    def read(self, *_: object) -> str:
        raise AssertionError("stdin was read although lines were given")

    @property
    def buffer(self) -> _OpenStdin:
        return self


def test_stdin_is_not_read_when_lines_are_given(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.stdin", _OpenStdin())
    assert main(["a=1"]) == 0
    assert [entry["cookie"]["name"] for entry in json.loads(capsys.readouterr().out)] == ["a"]


def test_the_command_does_not_wait_on_an_open_stdin_when_lines_are_given() -> None:
    command = [sys.executable, "-m", "setcookie", "a=1"]
    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as child:
        try:
            code = child.wait(timeout=60)
        except subprocess.TimeoutExpired:
            child.kill()
            pytest.fail("the command waited on stdin although a line was given")
    assert code == 0
