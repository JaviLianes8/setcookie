"""A consumer type-checks against the package with mypy --strict, and wrong use is caught."""

from __future__ import annotations

from pathlib import Path

import pytest

api = pytest.importorskip("mypy.api")

SRC = Path(__file__).resolve().parents[1] / "src"
GOOD = """
from datetime import datetime, timezone
from setcookie import Cookie, CookieError, SameSite, StoredCookie, build, parse, parse_date, receive

policy: SameSite = "Lax"
header: str = build("sid", "abc", same_site=policy, extensions=[("Priority", "High")])
cookie: Cookie = parse(header, strict=True)
when: datetime | None = parse_date("Wed, 09 Jun 2021 10:18:14 GMT")
stored: StoredCookie = receive(header, "https://h.test/", now=datetime.now(timezone.utc))
flag: bool = stored.matches("https://h.test/") and stored.is_expired(datetime.now(timezone.utc))
error: ValueError = CookieError("x")
age: int | None = cookie.max_age
"""
BAD = """
from setcookie import build, parse
build("sid", "abc", same_site="lax")
build("sid", "abc", max_age="60")
parse("a=b").same_site.lower()
"""


def _check(code: str, tmp_path: Path) -> tuple[str, int]:
    target = tmp_path / "consumer.py"
    target.write_text(code, encoding="utf-8")
    cache = tmp_path / "cache"
    out, err, status = api.run(
        ["--strict", "--no-incremental", "--cache-dir", str(cache), str(target)]
    )
    return out + err, status


def test_a_correct_consumer_type_checks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MYPYPATH", str(SRC))
    output, status = _check(GOOD, tmp_path)
    assert status == 0, output


def test_wrong_use_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MYPYPATH", str(SRC))
    output, status = _check(BAD, tmp_path)
    assert status == 1
    assert output.count("error:") == 3, output
