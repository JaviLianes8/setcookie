"""The command reads stdin only when no Set-Cookie line is given on the command line."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

import setcookie
from setcookie._cli import main

# The child imports the setcookie under test, not whatever copy is installed.
_ENV = {**os.environ, "PYTHONPATH": os.path.dirname(os.path.dirname(setcookie.__file__))}


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
    with subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=_ENV
    ) as child:
        try:
            code = child.wait(timeout=60)
        except subprocess.TimeoutExpired:
            child.kill()
            pytest.fail("the command waited on stdin although a line was given")
    assert code == 0


def test_the_last_byte_of_stdin_is_kept_without_a_final_newline() -> None:
    # printf '%s' and echo -n give input with no newline at the end.
    command = [sys.executable, "-m", "setcookie"]
    done = subprocess.run(command, input=b"a=1", capture_output=True, env=_ENV, check=False)
    assert done.returncode == 0, done.stderr
    report = json.loads(done.stdout)
    assert [(entry["cookie"]["name"], entry["cookie"]["value"]) for entry in report] == [("a", "1")]


def test_the_json_output_ends_with_a_newline() -> None:
    done = subprocess.run(
        [sys.executable, "-m", "setcookie", "a=1"], capture_output=True, env=_ENV, check=False
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.endswith(b"\n") and done.stdout.rstrip().endswith(b"]")
