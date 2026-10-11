from datetime import datetime, timedelta, timezone

import pytest

from setcookie import build


def test_build_minimal_pair_keeps_the_default_path() -> None:
    assert build("sid", "abc") == "sid=abc; Path=/"


def test_build_without_a_path_omits_the_attribute() -> None:
    assert build("sid", "abc", path=None) == "sid=abc"


def test_build_full_header_orders_attributes() -> None:
    header = build(
        "sid",
        "abc",
        max_age=3600,
        domain="example.com",
        path="/app",
        secure=True,
        http_only=True,
        same_site="Lax",
        expires=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
    )
    assert header == (
        "sid=abc; Expires=Fri, 02 Jan 2026 03:04:05 GMT; Max-Age=3600; "
        "Domain=example.com; Path=/app; Secure; HttpOnly; SameSite=Lax"
    )


def test_build_renders_samesite_none() -> None:
    assert build("sid", "abc", path=None, same_site="None") == "sid=abc; SameSite=None"


def test_build_flags_are_absent_when_false() -> None:
    assert "Secure" not in build("sid", "abc")
    assert "HttpOnly" not in build("sid", "abc")


def test_build_formats_expires_in_gmt_from_a_non_utc_zone() -> None:
    offset = timezone(timedelta(hours=2))
    moment = datetime(2026, 1, 2, 5, 4, 5, tzinfo=offset)
    header = build("sid", "abc", path=None, expires=moment)
    assert header == "sid=abc; Expires=Fri, 02 Jan 2026 03:04:05 GMT"


def test_build_rejects_an_empty_name() -> None:
    with pytest.raises(ValueError):
        build("", "abc")
