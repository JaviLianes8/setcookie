"""Boundaries and spellings that the QA mutation round showed were not pinned."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from setcookie import CookieError, build, expire, parse, receive

NOW = datetime(2026, 10, 13, tzinfo=timezone.utc)


def test_a_lone_double_quote_is_not_a_quoted_value() -> None:
    with pytest.raises(CookieError, match="U\\+0022 at index 0"):
        build("a", '"')
    with pytest.raises(CookieError, match="U\\+0022 at index 0"):
        parse('a="', strict=True)
    assert build("a", '""') == 'a=""; Path=/'
    assert parse('a=""', strict=True).value == '""'


def test_expire_passes_every_flag_through() -> None:
    assert expire("sid", secure=True, partitioned=True) == (
        "sid=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/; Secure; Partitioned"
    )
    assert expire("sid", domain="h.example", path=None, http_only=True, same_site="Lax") == (
        "sid=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Domain=h.example; HttpOnly; SameSite=Lax"
    )


@pytest.mark.parametrize("spelling", ["none", "NONE", "nOnE"])
def test_strict_same_site_none_needs_secure_in_any_case(spelling: str) -> None:
    with pytest.raises(CookieError, match=r"^strict: SameSite=None needs the Secure attribute$"):
        parse(f"a=b; SameSite={spelling}", strict=True)
    assert parse(f"a=b; SameSite={spelling}; Secure", strict=False).same_site == "None"


@pytest.mark.parametrize("name", ["__hostname", "__secured", "__Host", "__Secure", "__host_x"])
def test_a_name_that_only_starts_like_a_prefix_has_no_prefix_rules(name: str) -> None:
    assert build(name, "x") == f"{name}=x; Path=/"
    assert receive(f"{name}=x; Domain=h.example", "http://h.example/", now=NOW).name == name
    assert parse(f"{name}=x", strict=True).name == name


def test_max_age_past_the_end_of_the_calendar_clamps_to_the_latest_time() -> None:
    late = datetime(9999, 12, 31, tzinfo=timezone.utc)
    stored = receive("a=b; Max-Age=34560000", "https://h.example/", now=late)
    assert stored.expiry == datetime.max.replace(tzinfo=timezone.utc)
    assert not stored.is_expired(late)


def test_build_accepts_expires_from_the_first_day_of_1601() -> None:
    assert build("a", "b", expires=datetime(1601, 1, 1)) == (
        "a=b; Expires=Mon, 01 Jan 1601 00:00:00 GMT; Path=/"
    )
    with pytest.raises(CookieError, match=r"^expires before the year 1601"):
        build("a", "b", expires=datetime(1600, 12, 31, 23, 59, 59))


def test_build_size_limits_raise_its_own_messages_at_the_boundary() -> None:
    assert build("a", "b" * 4095).startswith("a=")
    with pytest.raises(CookieError, match=r"^the name and value are longer than 4096 octets"):
        build("a", "b" * 4096)
    assert build("a", "b", path="/" + "p" * 1023).endswith("p")
    with pytest.raises(CookieError, match=r"^path value is longer than 1024 octets$"):
        build("a", "b", path="/" + "p" * 1024)
    with pytest.raises(CookieError, match=r"^extension 'k' value is longer than 1024 octets$"):
        build("a", "b", extensions=[("k", "v" * 1025)])
