"""Boundaries of the host name rule and the cookie date fields, pinned exactly."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from setcookie import CookieError, build, parse, parse_date


def test_a_domain_label_may_have_63_characters_but_not_64() -> None:
    longest = "a" * 63 + ".example"
    assert build("sid", "v", domain=longest).endswith(f"Domain={longest}; Path=/")
    assert parse(f"sid=v; Domain={longest}", strict=True).domain == longest
    for domain in ("a" * 64 + ".example", "x." + "b" * 64):
        with pytest.raises(CookieError, match="not a host name"):
            build("sid", "v", domain=domain)
        with pytest.raises(CookieError, match="not a host name"):
            parse(f"sid=v; Domain={domain}", strict=True)


def test_a_domain_may_have_253_characters_but_not_254() -> None:
    name = ".".join(["a" * 63] * 3) + "." + "b" * 61
    assert len(name) == 253
    assert build("sid", "v", domain=name)
    for domain in (name + "c", "-a.example", "a-.example", "a..example", "a_b.example"):
        with pytest.raises(CookieError):
            build("sid", "v", domain=domain)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("23:59:59 31 Dec 2037", datetime(2037, 12, 31, 23, 59, 59, tzinfo=timezone.utc)),
        ("0:0:0 1 Jan 1601", datetime(1601, 1, 1, tzinfo=timezone.utc)),
        ("24:00:00 1 Jan 2030", None),
        ("23:60:00 1 Jan 2030", None),
        ("23:00:60 1 Jan 2030", None),
        ("00:00:00 32 Jan 2030", None),
        ("00:00:00 0 Jan 2030", None),
        ("00:00:00 29 Feb 2028", datetime(2028, 2, 29, tzinfo=timezone.utc)),
        ("00:00:00 29 Feb 2030", None),
    ],
)
def test_date_fields_stop_at_their_ranges(text: str, expected: datetime | None) -> None:
    assert parse_date(text) == expected
