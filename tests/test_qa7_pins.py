"""Contracts the second QA round of the second full pass found missing (mutants that survived)."""

from __future__ import annotations

import errno
import io
import os
import subprocess
import sys
from datetime import datetime, timezone

import pytest

import setcookie
from setcookie import CookieError, receive
from setcookie._cli import SIGPIPE_STATUS, main

NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)
ENV = {**os.environ, "PYTHONPATH": os.path.dirname(os.path.dirname(setcookie.__file__))}


@pytest.mark.parametrize("host", ["[v1.abc]", "[v7.x-y]"])
def test_a_bracketed_host_must_be_an_ipv6_address(host: str) -> None:
    with pytest.raises(CookieError, match="cannot be canonicalized"):
        receive("a=1", f"https://{host}/", now=NOW)


@pytest.mark.parametrize("dot", ["\u3002", "\uff0e", "\uff61"])
def test_an_ideographic_full_stop_separates_labels_for_the_dns_bound(dot: str) -> None:
    host = "a" * 40 + dot + "b" * 40 + ".com"
    assert receive("a=1", f"https://{host}/", now=NOW).domain == "a" * 40 + "." + "b" * 40 + ".com"


def test_a_lone_surrogate_in_the_path_becomes_the_replacement_character() -> None:
    assert receive("a=1", "https://h.example/\ud800/x", now=NOW).path == "/%EF%BF%BD"


class _Lying(str):
    def lstrip(self, chars: str | None = None) -> str:
        return "https://evil.example/"

    def strip(self, chars: str | None = None) -> str:
        return "https://evil.example/"

    def replace(self, old: str, new: str, count: int = -1) -> str:  # type: ignore[override]
        return "https://evil.example/"

    def partition(self, sep: str) -> tuple[str, str, str]:
        return ("https", ":", "//evil.example/")


def test_a_str_subclass_cannot_redirect_the_request_url() -> None:
    url = _Lying("https://example.com/")
    assert receive("a=1", url, now=NOW).domain == "example.com"
    assert receive("a=1", "https://example.com/", now=NOW).matches(url)
    assert not receive("a=1", "https://evil.example/", now=NOW).matches(url)


def test_the_host_length_bound_is_253_characters() -> None:
    fits = ".".join(["a" * 63] * 3 + ["b" * 61])
    assert receive("a=1", f"https://{fits}/", now=NOW).domain == fits
    with pytest.raises(CookieError, match="cannot be canonicalized"):
        receive("a=1", "https://" + ".".join(["a" * 63] * 3 + ["b" * 62]) + "/", now=NOW)


def test_the_label_bound_applies_before_idna_mapping() -> None:
    with pytest.raises(CookieError, match="cannot be canonicalized"):
        receive("a=1", "https://" + "a" * 63 + "\u00ad.com/", now=NOW)


def test_a_final_dot_segment_of_the_request_path_is_empty() -> None:
    stored = receive("a=1; Path=/a/.", "https://h.example/", now=NOW)
    assert not stored.matches("https://h.example/a/.")
    stored = receive("a=1; Path=/a/b/..", "https://h.example/", now=NOW)
    assert not stored.matches("https://h.example/a/b/..")
    assert receive("a=1", "https://h.example/a/b/../c", now=NOW).path == "/a"


def test_a_tilde_is_not_encoded_in_the_path() -> None:
    assert receive("a=1", "https://h.example/~u/x", now=NOW).path == "/~u"
    assert receive("a=1; Path=/~u", "https://h.example/", now=NOW).matches("https://h.example/~u/x")


@pytest.mark.parametrize("dots", ["..", ".%2e", "%2e.", "%2e%2e", ".%2E", "%2E.", "%2E%2E"])
def test_every_spelling_of_a_double_dot_segment_is_resolved(dots: str) -> None:
    assert receive("a=1", f"https://h.example/a/{dots}/b/c", now=NOW).path == "/b"


def _closed_pipe_status(args: list[str], close: str) -> tuple[int, str]:
    out = subprocess.DEVNULL if close == "stderr" else subprocess.PIPE
    with subprocess.Popen(
        [sys.executable, "-m", "setcookie", *args],
        stdin=subprocess.DEVNULL,
        stdout=out,
        stderr=subprocess.PIPE,
        env=ENV,
    ) as child:
        assert child.stderr
        if close == "stdout":
            assert child.stdout
            child.stdout.close()
            err = child.stderr.read().decode("utf-8", "replace")
        else:
            child.stderr.close()
            err = ""
        return child.wait(timeout=120), err


def test_a_closed_output_pipe_stops_quietly_after_one_short_line() -> None:
    code, err = _closed_pipe_status(["a=1"], "stdout")
    assert code == SIGPIPE_STATUS and err == "", err


def test_a_closed_error_pipe_stops_quietly() -> None:
    code, _ = _closed_pipe_status(["--url", "http://h.example/", "a=1; Secure"], "stderr")
    assert code == SIGPIPE_STATUS


class _Full(io.StringIO):
    def write(self, text: str) -> int:
        raise OSError(errno.ENOSPC, "No space left on device")


def test_an_output_error_other_than_a_closed_pipe_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("sys.stdout", _Full())
    with pytest.raises(OSError) as raised:
        main(["a=1"])
    assert raised.value.errno == errno.ENOSPC
