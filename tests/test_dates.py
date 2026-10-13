"""The cookie-date algorithm of section 5.1.1. Inputs are written by hand from the grammar."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from setcookie import parse_date
from setcookie._dates import format_http_date, parse_fixdate


def utc(
    year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0
) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Sun, 06 Nov 1994 08:49:37 GMT", utc(1994, 11, 6, 8, 49, 37)),
        ("Sunday, 06-Nov-94 08:49:37 GMT", utc(1994, 11, 6, 8, 49, 37)),
        ("Sun Nov  6 08:49:37 1994", utc(1994, 11, 6, 8, 49, 37)),
        ("Fri Jan 01 2038 00:00:00 GMT", utc(2038, 1, 1)),
        ("Fri Jan 01 03:14:07 2038", utc(2038, 1, 1, 3, 14, 7)),
        ("Thu Apr 10 1980 16:33:12 GMT-0700 (PDT)", utc(1980, 4, 10, 16, 33, 12)),
        ("Wed, 09 Jun 2021 10:18:14 +0200", utc(2021, 6, 9, 10, 18, 14)),
        ("1 jAnUaRy 2030 1:2:3", utc(2030, 1, 1, 1, 2, 3)),
        ("09 Jun 69 00:00:00", utc(2069, 6, 9)),
        ("09 Jun 70 00:00:00", utc(1970, 6, 9)),
        ("09 Jun 00 00:00:00", utc(2000, 6, 9)),
        ("01 Jan 1601 00:00:00", utc(1601, 1, 1)),
        ("29 Feb 2024 23:59:59", utc(2024, 2, 29, 23, 59, 59)),
        ("10:00:00xyz 5th Junk 2030abc", utc(2030, 6, 5, 10)),
        (";;Mon,, 06 Nov 2023 08:49:37 GMT;;", utc(2023, 11, 6, 8, 49, 37)),
    ],
)
def test_parse_date_accepts(text: str, expected: datetime) -> None:
    assert parse_date(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "never",
        "06 Nov 1994",
        "Nov 1994 08:49:37",
        "06 1994 08:49:37",
        "06 Nov 08:49:37",
        "01 Jan 1600 00:00:00",
        "32 Jan 2030 00:00:00",
        "00 Jan 2030 00:00:00",
        "30 Feb 2030 00:00:00",
        "29 Feb 2023 00:00:00",
        "01 Jan 2030 24:00:00",
        "01 Jan 2030 23:60:00",
        "01 Jan 2030 23:59:60",
        "001 Jan 2030 00:00:00",
        "01 Jan 20300 00:00:00",
        "01 Jan 2030 000:00:00",
        "\uff10\uff11 Jan 2030 00:00:00",
        "2021-06-09 10:18:14",
    ],
)
def test_parse_date_rejects(text: str) -> None:
    assert parse_date(text) is None


def test_the_first_token_of_each_kind_wins() -> None:
    # "12" is the day, "13" the two-digit year 2013, and the later "2030" is ignored.
    assert parse_date("12 13 Jan 2030 00:00:00") == utc(2013, 1, 12)
    # The second time token is read as a day of month ("04" then a non-digit).
    assert parse_date("01:02:03 04:05:06 1 Jan 2030") == utc(2030, 1, 4, 1, 2, 3)


def test_format_http_date_writes_an_imf_fixdate_in_gmt() -> None:
    moment = datetime(2026, 1, 2, 5, 4, 5, tzinfo=timezone(timedelta(hours=2)))
    assert format_http_date(moment) == "Fri, 02 Jan 2026 03:04:05 GMT"
    assert format_http_date(datetime(2026, 1, 2, 3, 4, 5)) == "Fri, 02 Jan 2026 03:04:05 GMT"


def test_parse_fixdate_is_exact() -> None:
    assert parse_fixdate("Sun, 06 Nov 1994 08:49:37 GMT") == utc(1994, 11, 6, 8, 49, 37)
    for text in (
        "Mon, 06 Nov 1994 08:49:37 GMT",
        "sun, 06 Nov 1994 08:49:37 GMT",
        "Sun, 6 Nov 1994 08:49:37 GMT",
        "Sun, 06 Nov 1994 08:49:37 UTC",
        "Sun, 31 Nov 1994 08:49:37 GMT",
        "Sun Nov  6 08:49:37 1994",
    ):
        assert parse_fixdate(text) is None, text
