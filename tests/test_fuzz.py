"""Seeded property tests: hostile lines never crash, and the codec agrees with itself."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import pytest

from setcookie import Cookie, CookieError, build, parse, parse_date, receive

SEEDS = [1, 20261020, 987654321]
NOW = datetime(2026, 10, 20, tzinfo=timezone.utc)
PIECES = [
    ";", ";", "=", "=", " ", "\t", '"', ",", "\\", "/", ".", "-", ":", "0", "7", "99", "a", "Z",
    "Expires", "max-age", "Domain", "PATH", "Secure", "httponly", "SameSite", "Partitioned",
    "__Host-", "__secure-", "Lax", "none", "STRICT", "GMT", "Jan", "1970", "23:59:59", "+5",
    "\x00", "\x01", "\r", "\n", "\x7f", "\u00e9", "\u00a0", "\ud800", "\U0001f600", "xn--",
    "example.com", ".Example.COM", "Fri, 01 Jan 2038 00:00:00 GMT", "x" * 1100,
]  # fmt: skip
URLS = [
    "https://example.com/", "http://www.example.com/a/b", "https://sub.example.com",
    "wss://example.com/x/", "https://127.0.0.1/p", "https://[::1]/", "https://xn--zz.de/",
    "https://B\u00fccher.example/", "file:///etc", "https://[::1/", "", "https://site.example/a",
]  # fmt: skip


def _line(rng: random.Random) -> str:
    return "".join(rng.choice(PIECES) for _ in range(rng.randint(0, 24)))


@pytest.mark.parametrize("seed", SEEDS)
def test_parse_never_raises_anything_but_cookie_error(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(4000):
        line = _line(rng)
        for strict in (False, True):
            try:
                cookie = parse(line, strict=strict)
            except CookieError as error:
                assert len(str(error)) < 300
                continue
            assert isinstance(cookie, Cookie)
            assert cookie.name == cookie.name.strip(" \t")
            assert cookie.same_site in (None, "Lax", "Strict", "None")


@pytest.mark.parametrize("seed", SEEDS)
def test_a_strict_line_rebuilds_to_the_same_cookie(seed: int) -> None:
    rng = random.Random(seed)
    accepted = 0
    for _ in range(20000):
        line = "a=b" + "".join(rng.choice(PIECES[:40]) for _ in range(rng.randint(0, 8)))
        try:
            cookie = parse(line, strict=True)
        except CookieError:
            continue
        accepted += 1
        assert parse(line) == cookie
        assert parse(cookie.header(), strict=True) == cookie
    assert accepted > 50


def _random_build(rng: random.Random) -> dict[str, object]:
    options: dict[str, object] = {}
    if rng.random() < 0.3:
        options["expires"] = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(
            seconds=rng.randrange(0, 2**37)
        )
    if rng.random() < 0.3:
        options["max_age"] = rng.choice([1, 59, 34560000, 10**30])
    if rng.random() < 0.3:
        options["domain"] = rng.choice(["example.com", "a-b.c0", "1.2.3.4", "x"])
    options["path"] = rng.choice([None, "/", "", "/a/b", "/~x!"])
    for flag in ("secure", "http_only", "partitioned"):
        options[flag] = rng.random() < 0.5
    options["same_site"] = rng.choice([None, "Lax", "Strict", "None"])
    options["extensions"] = rng.choice([(), (("Priority", "High"),), (("x-y", None),)])
    return options


@pytest.mark.parametrize("seed", SEEDS)
def test_whatever_build_writes_parses_back_to_its_arguments(seed: int) -> None:
    rng = random.Random(seed)
    names = ["sid", "__Secure-x", "__Host-x", "a!#$%&'*+-.^_`|~z"]
    values = ["", "v", '"q"', "x=y:z/w?!#", "".join(map(chr, range(0x23, 0x2B)))]
    written = 0
    for _ in range(3000):
        name, value, options = rng.choice(names), rng.choice(values), _random_build(rng)
        try:
            header = build(name, value, **options)  # type: ignore[arg-type]
        except CookieError:
            continue
        written += 1
        cookie = parse(header, strict=True)
        assert (cookie.name, cookie.value) == (name, value)
        assert cookie.max_age == options.get("max_age")
        assert cookie.domain == options.get("domain")
        assert cookie.path == options["path"]
        assert (cookie.secure, cookie.http_only) == (options["secure"], options["http_only"])
        assert cookie.same_site == options["same_site"]
        assert cookie.extensions == options["extensions"]
        expires = options.get("expires")
        assert cookie.expires == (expires.replace(microsecond=0) if expires else None)  # type: ignore[attr-defined]
    assert written > 500


@pytest.mark.parametrize("seed", SEEDS)
def test_parse_date_returns_none_or_an_aware_utc_date_after_1600(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(20000):
        text = "".join(rng.choice([*PIECES[:40], " ", "12", "31", "2038"]) for _ in range(9))
        moment = parse_date(text)
        assert moment is None or (moment.tzinfo is timezone.utc and moment.year >= 1601)


@pytest.mark.parametrize("seed", SEEDS)
def test_receive_never_raises_anything_but_cookie_error(seed: int) -> None:
    rng = random.Random(seed)
    stored_count = 0
    for _ in range(3000):
        url, line = rng.choice(URLS), _line(rng)
        try:
            stored = receive(line, url, now=NOW, cross_site=rng.random() < 0.2)
        except CookieError as error:
            assert len(str(error)) < 300
            continue
        stored_count += 1
        assert stored.persistent == (stored.expiry is not None)
        assert stored.path.startswith("/")
        if not parse(line).path:
            # Without a usable Path the cookie lands on the directory of the request.
            assert stored.matches(url)
    assert stored_count > 100
