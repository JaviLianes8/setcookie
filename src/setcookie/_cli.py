"""Command line: read Set-Cookie lines and print what they mean as JSON."""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from ._errors import CookieError
from ._parse import parse
from ._store import receive

_HEADER = re.compile(r"set-cookie[ \t]*:[ \t]*(.*)", re.IGNORECASE | re.DOTALL)


def _lines(args: Sequence[str], stdin: str) -> list[str]:
    """Explicit lines, or stdin; from a header dump only the Set-Cookie fields are kept."""
    if args:
        return list(args)
    raw = [line.rstrip("\r") for line in stdin.split("\n")]
    headers = [match[1] for line in raw if (match := _HEADER.fullmatch(line))]
    return headers if headers else [line for line in raw if line.strip()]


def _plain(value: object) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _fields(record: Any) -> dict[str, Any]:
    return {field.name: _plain(getattr(record, field.name)) for field in dataclasses.fields(record)}


def _report(line: str, options: argparse.Namespace) -> tuple[dict[str, Any], bool]:
    entry: dict[str, Any] = {"line": line}
    try:
        entry["cookie"] = _fields(parse(line, strict=options.strict))
        if options.url:
            entry["stored"] = _fields(receive(line, options.url, now=options.now))
    except CookieError as error:
        entry["error"] = str(error)
        return entry, False
    return entry, True


def _moment(text: str) -> datetime:
    moment = datetime.fromisoformat(text)
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point of the ``setcookie`` command; returns the exit status."""
    parser = argparse.ArgumentParser(
        prog="setcookie",
        description="Parse Set-Cookie lines (arguments, or stdin such as a curl -sI dump).",
    )
    parser.add_argument("lines", nargs="*", help="Set-Cookie values; read stdin when absent")
    parser.add_argument("--strict", action="store_true", help="check the server grammar")
    parser.add_argument("--url", help="show what a user agent stores for this request URL")
    parser.add_argument(
        "--now", type=_moment, default=None, help="ISO time for --url (default: the clock)"
    )
    options = parser.parse_args(argv)
    if options.now is None:
        options.now = datetime.now(timezone.utc)
    lines = _lines(options.lines, "" if options.lines else sys.stdin.read())
    if not lines:
        parser.error("no Set-Cookie line given")
    reports = [_report(line, options) for line in lines]
    json.dump([entry for entry, _ in reports], sys.stdout, indent=2)
    sys.stdout.write("\n")
    failures = [entry["error"] for entry, ok in reports if not ok]
    for reason in failures:
        print(f"setcookie: {reason}", file=sys.stderr)
    return 1 if failures else 0
