from datetime import datetime, timezone

import pytest

from setcookie import Cookie, CookieError, build, parse


def test_parse_minimal_pair() -> None:
    cookie = parse("sid=abc")
    assert cookie.name == "sid"
    assert cookie.value == "abc"
    assert cookie.path is None


def test_parse_reads_every_attribute() -> None:
    cookie = parse(
        "sid=abc; Expires=Fri, 02 Jan 2026 03:04:05 GMT; Max-Age=3600; "
        "Domain=example.com; Path=/app; Secure; HttpOnly; SameSite=Strict"
    )
    assert cookie == Cookie(
        name="sid",
        value="abc",
        expires=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        max_age=3600,
        domain="example.com",
        path="/app",
        secure=True,
        http_only=True,
        same_site="Strict",
    )


def test_parse_is_case_insensitive_on_attribute_names() -> None:
    cookie = parse("sid=abc; secure; HTTPONLY; samesite=lax; max-age=10")
    assert cookie.secure is True
    assert cookie.http_only is True
    assert cookie.same_site == "Lax"
    assert cookie.max_age == 10


def test_parse_tolerates_a_malformed_max_age() -> None:
    assert parse("sid=abc; Max-Age=soon").max_age is None


def test_parse_tolerates_an_unparseable_expires() -> None:
    assert parse("sid=abc; Expires=never").expires is None


def test_parse_ignores_unknown_attributes() -> None:
    cookie = parse("sid=abc; Priority=High; Path=/")
    assert cookie.path == "/"


def test_parse_rejects_a_line_without_a_pair() -> None:
    with pytest.raises(CookieError):
        parse("Secure; HttpOnly")


def test_parse_rejects_an_empty_name() -> None:
    with pytest.raises(CookieError):
        parse("=abc; Path=/")


def test_round_trip_through_build_and_parse() -> None:
    header = build(
        "sid",
        "abc",
        max_age=600,
        domain="example.com",
        path="/app",
        secure=True,
        http_only=True,
        same_site="None",
        expires=datetime(2030, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
    )
    assert parse(header) == Cookie(
        name="sid",
        value="abc",
        expires=datetime(2030, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        max_age=600,
        domain="example.com",
        path="/app",
        secure=True,
        http_only=True,
        same_site="None",
    )
